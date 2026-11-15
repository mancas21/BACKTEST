# WAVE_1 scalp pack (scalp_wave1 v1.1.0) — ported and measured

- generated: `2026-11-11T18:21:38Z`
- source: `Downloads/scalp_wave1_v1.1.0/wave1` (Python-only pack v1.1.0)
- engine: `code/scalp_wave_engine.py` (sha256 `68d25770bef3d6db`)
- adapter: `scalpwave` in `code/vrun.py`
- costs: repo standard — 5 bps fee + 0.5 bps slip per side (11 bps round trip), charged on entry and on exit
- funding: **not charged** (the pack is kline-only and carries no funding input) — a declared limit of the port, not a silent omission

## Verdict (REGLA 1: this pack is judged ONLY on its own artifacts)

**KILLED.**

- Every cell loses at repo costs: 15 of 15 cells have a negative net return.
- Every cell also loses at ZERO cost: 15 of 15 cells have a negative net return with no fees at all. This is not a cost problem a better fill model could fix — the signals themselves are negative-expectancy.
- The best cell's PF ex-cost is 0.8624 (SUIUSDT 15m); the repo's gate is above one.
- The best single signal family across every cell has a PF ex-cost of 1.0059: above one but below the repo's gate, and it is the MAXIMUM over every family×cell combination measured, i.e. the best of many draws rather than a result.

The source pack anticipated this outcome for its reversion signals: its own spec says a study may classify the extension signals ANTI-INFORMATIVE if the extension keeps going, and calls that a finding rather than a defect. The measurement agrees.

## Cells

| symbol | tf | window | n | net % | PF ex-cost | win % | max DD % | zero-cost net % | drag pp | commission/gross % | run_id |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| SOLUSDT | 1m | 2025-11-06..2026-11-06 | 1871 | -88.26 | 0.7232 | 31.2 | -96.23 | -16.21 | 72.06 | 32.5 | `628e8d2fdd6fcbb9` |
| SUIUSDT | 1m | 2025-11-06..2026-11-06 | 2548 | -93.20 | 0.7463 | 31.4 | -97.89 | -6.05 | 87.15 | 31.6 | `28735e7746de83ac` |
| HYPEUSDT | 1m | 2025-11-06..2026-11-06 | 2804 | -97.95 | 0.7004 | 30.1 | -99.34 | -58.45 | 39.50 | 31.6 | `772e4214494ba358` |
| BTCUSDT *(contexto)* | 1m | 2025-11-06..2026-11-06 | 1139 | -71.66 | 0.7291 | 30.7 | -90.66 | -0.32 | 71.34 | 35.9 | `796579b77d6df8c0` |
| SOLUSDT | 5m | 2020-09-14..2026-11-06 | 18590 | -100 | 0.7757 | 31 | -100 | -98.58 | 1.42 | 19.8 | `f36ea24e4dbaf5f9` |
| SUIUSDT | 5m | 2023-05-03..2026-11-06 | 10039 | -100 | 0.7915 | 31.4 | -100 | -83.02 | 16.98 | 25.9 | `7a8e4006da88f6ce` |
| HYPEUSDT | 5m | 2025-05-30..2026-11-06 | 4352 | -99.41 | 0.7339 | 30.7 | -99.81 | -40.63 | 58.78 | 27.3 | `5a84a94cb0db4941` |
| BTCUSDT *(contexto)* | 5m | 2019-09-08..2026-11-06 | 15512 | -100 | 0.6644 | 31.1 | -100 | -87.08 | 12.92 | 39.6 | `e5e63789aa7b881b` |
| SOLUSDT | 15m | 2020-09-14..2026-11-10 | 10477 | -100 | 0.8213 | 29.9 | -100 | -97.83 | 2.17 | 14.4 | `b99fd9a5ef57871c` |
| SUIUSDT | 15m | 2023-05-03..2026-11-10 | 5627 | -99.73 | 0.8624 | 31.3 | -99.93 | -11.81 | 87.92 | 18.8 | `2d4064eeea7e9785` |
| HYPEUSDT | 15m | 2025-05-30..2026-11-10 | 2589 | -96.36 | 0.8160 | 30.1 | -99 | -48.85 | 47.51 | 20.2 | `17e31ae19837a1ec` |
| BTCUSDT *(contexto)* | 15m | 2019-09-08..2026-11-10 | 10940 | -100 | 0.7312 | 30.6 | -100 | -67.45 | 32.55 | 32.8 | `33298ec622bfbd25` |

Artifacts: `results/runs/<run_id>` (one per cell; the run_id column names the file).

## Sensitivity cells

Same engine, different declared parameters. A variant never replaces a primary cell.

| symbol | tf | params | n | net % | PF ex-cost | max DD % | run_id |
|---|---|---|---:|---:|---:|---:|---|
| SOLUSDT | 5m | `gate_cost=pack` | 17226 | -100 | 0.7715 | -100 | `b5508330cf8436d2` |
| SOLUSDT | 5m | `regime_filter=True` | 16008 | -100 | 0.7830 | -100 | `a3ba999fbaa607f5` |
| SUIUSDT | 5m | `gate_cost=pack` | 8705 | -100 | 0.8121 | -100 | `fd8301a9c82108cd` |

## Signal families

The source pack's own study design analyses each signal family separately, so the aggregate alone would hide which family carries the loss. Measured inside each artifact at repo costs, one position at a time.

### SOLUSDT 1m

| family | n | net % | PF ex-cost | win % | max DD % |
|---|---:|---:|---:|---:|---:|
| `IND-06:SWEEP_BEAR` | 71 | -9.14 | 0.3631 | 19.7 | -69.99 |
| `IND-07a:SQZ_REL_SHORT` | 99 | -9.27 | 0.6167 | 35.4 | -70.38 |
| `IND-07a:SQZ_REL_LONG` | 99 | -12.32 | 0.5124 | 32.3 | -14.34 |
| `IND-06:SWEEP_BULL` | 111 | -14.81 | 0.3730 | 20.7 | -15.15 |
| `IND-07a:BURST_UP` | 424 | -30.19 | 0.6925 | 35.6 | -34.82 |
| `IND-07a:BURST_DN` | 481 | -48.81 | 0.5391 | 30.6 | -82.96 |
| `IND-04:VWAP_EXT_UP` | 743 | -54.41 | 0.7921 | 31.4 | -85.56 |
| `IND-04:VWAP_EXT_DN` | 724 | -57.05 | 0.7464 | 32 | -58.17 |

Artifact: `results/runs/628e8d2fdd6fcbb9`

### SUIUSDT 1m

| family | n | net % | PF ex-cost | win % | max DD % |
|---|---:|---:|---:|---:|---:|
| `IND-06:SWEEP_BEAR` | 124 | -11.58 | 0.5385 | 26.6 | -70.72 |
| `IND-06:SWEEP_BULL` | 162 | -14.55 | 0.5581 | 25.3 | -15.66 |
| `IND-07a:SQZ_REL_LONG` | 227 | -30.03 | 0.4666 | 29.5 | -30.03 |
| `IND-07a:SQZ_REL_SHORT` | 252 | -31.25 | 0.4837 | 28.6 | -77.30 |
| `IND-04:VWAP_EXT_UP` | 797 | -33.05 | 0.8957 | 34 | -80.26 |
| `IND-07a:BURST_UP` | 640 | -50.89 | 0.6217 | 32.5 | -52.31 |
| `IND-04:VWAP_EXT_DN` | 799 | -61.49 | 0.7640 | 30.3 | -64.58 |
| `IND-07a:BURST_DN` | 822 | -68.07 | 0.5366 | 30.8 | -89.43 |

Artifact: `results/runs/28735e7746de83ac`

### HYPEUSDT 1m

| family | n | net % | PF ex-cost | win % | max DD % |
|---|---:|---:|---:|---:|---:|
| `IND-06:SWEEP_BEAR` | 218 | -22.88 | 0.4362 | 22.9 | -74.24 |
| `IND-06:SWEEP_BULL` | 257 | -26.04 | 0.4546 | 25.3 | -26.66 |
| `IND-07a:SQZ_REL_LONG` | 302 | -31.87 | 0.5278 | 31.5 | -33.24 |
| `IND-07a:SQZ_REL_SHORT` | 322 | -33.82 | 0.5464 | 31.4 | -78.20 |
| `IND-04:VWAP_EXT_DN` | 744 | -52.02 | 0.8140 | 31.5 | -58.14 |
| `IND-07a:BURST_UP` | 777 | -59.04 | 0.5726 | 33.1 | -59.42 |
| `IND-07a:BURST_DN` | 950 | -74.05 | 0.5286 | 29.9 | -91.35 |
| `IND-04:VWAP_EXT_UP` | 911 | -84.42 | 0.6692 | 27.4 | -94.91 |

Artifact: `results/runs/772e4214494ba358`

### SOLUSDT 5m

| family | n | net % | PF ex-cost | win % | max DD % |
|---|---:|---:|---:|---:|---:|
| `IND-06:SWEEP_BEAR` | 1569 | -82 | 0.7046 | 29.6 | -94.14 |
| `IND-06:SWEEP_BULL` | 1778 | -84.89 | 0.7616 | 29.6 | -87.15 |
| `IND-07a:SQZ_REL_SHORT` | 4659 | -98.65 | 0.8354 | 33.8 | -99.59 |
| `IND-07a:BURST_UP` | 3718 | -99.07 | 0.7688 | 31.9 | -99.13 |
| `IND-07a:SQZ_REL_LONG` | 4505 | -99.55 | 0.8019 | 32.1 | -99.57 |
| `IND-04:VWAP_EXT_UP` | 4194 | -99.58 | 0.7199 | 29.8 | -99.87 |
| `IND-07a:BURST_DN` | 4343 | -99.76 | 0.6995 | 32.1 | -99.92 |
| `IND-04:VWAP_EXT_DN` | 4165 | -99.84 | 0.7076 | 27.9 | -99.84 |

Artifact: `results/runs/f36ea24e4dbaf5f9`

### SUIUSDT 5m

| family | n | net % | PF ex-cost | win % | max DD % |
|---|---:|---:|---:|---:|---:|
| `IND-06:SWEEP_BEAR` | 717 | -64.65 | 0.5998 | 28.2 | -88.36 |
| `IND-06:SWEEP_BULL` | 702 | -66.62 | 0.5486 | 27.5 | -67.72 |
| `IND-07a:BURST_UP` | 1372 | -82.70 | 0.6991 | 32 | -82.70 |
| `IND-04:VWAP_EXT_UP` | 2402 | -92.06 | 0.8140 | 31.1 | -97.62 |
| `IND-07a:BURST_DN` | 1860 | -92.36 | 0.6751 | 32.7 | -97.66 |
| `IND-07a:SQZ_REL_LONG` | 2598 | -92.88 | 0.7809 | 32.7 | -93.28 |
| `IND-07a:SQZ_REL_SHORT` | 2676 | -95.69 | 0.6963 | 33 | -98.61 |
| `IND-04:VWAP_EXT_DN` | 2370 | -96.56 | 0.8159 | 28.6 | -96.76 |

Artifact: `results/runs/7a8e4006da88f6ce`

### HYPEUSDT 5m

| family | n | net % | PF ex-cost | win % | max DD % |
|---|---:|---:|---:|---:|---:|
| `IND-04:VWAP_EXT_DN` | 1018 | 3.08 | 1.0059 | 34.5 | -22.09 |
| `IND-06:SWEEP_BEAR` | 364 | -28.11 | 0.7149 | 30.8 | -76.50 |
| `IND-06:SWEEP_BULL` | 435 | -28.46 | 0.7452 | 30.3 | -29.83 |
| `IND-07a:BURST_UP` | 687 | -70.72 | 0.5756 | 28.5 | -71.96 |
| `IND-07a:BURST_DN` | 871 | -72.24 | 0.6595 | 32 | -90.98 |
| `IND-07a:SQZ_REL_LONG` | 1005 | -77.49 | 0.6033 | 30.7 | -77.74 |
| `IND-07a:SQZ_REL_SHORT` | 1009 | -79.35 | 0.5945 | 29.2 | -93.30 |
| `IND-04:VWAP_EXT_UP` | 1156 | -79.66 | 0.7603 | 30 | -94.18 |

Artifact: `results/runs/5a84a94cb0db4941`

### SOLUSDT 15m

| family | n | net % | PF ex-cost | win % | max DD % |
|---|---:|---:|---:|---:|---:|
| `IND-06:SWEEP_BULL` | 561 | -31.41 | 0.8487 | 35.1 | -40.12 |
| `IND-06:SWEEP_BEAR` | 584 | -53.30 | 0.7424 | 31.2 | -84.72 |
| `IND-07a:BURST_DN` | 1078 | -60.17 | 0.8371 | 34.4 | -87.74 |
| `IND-07a:BURST_UP` | 931 | -65.11 | 0.8222 | 32.5 | -66.38 |
| `IND-07a:SQZ_REL_SHORT` | 2479 | -87.48 | 0.8718 | 35.1 | -97.05 |
| `IND-07a:SQZ_REL_LONG` | 2360 | -96.36 | 0.7835 | 30.9 | -96.42 |
| `IND-04:VWAP_EXT_UP` | 3311 | -99.22 | 0.7604 | 27.9 | -99.76 |
| `IND-04:VWAP_EXT_DN` | 3279 | -99.36 | 0.7177 | 27.5 | -99.41 |

Artifact: `results/runs/b99fd9a5ef57871c`

### SUIUSDT 15m

| family | n | net % | PF ex-cost | win % | max DD % |
|---|---:|---:|---:|---:|---:|
| `IND-07a:BURST_UP` | 290 | -22.06 | 0.8581 | 34.8 | -22.28 |
| `IND-06:SWEEP_BEAR` | 211 | -29.42 | 0.6885 | 30.3 | -77.66 |
| `IND-07a:BURST_DN` | 405 | -36.69 | 0.8103 | 34.1 | -80.37 |
| `IND-06:SWEEP_BULL` | 205 | -39.89 | 0.5869 | 26.8 | -42.68 |
| `IND-07a:SQZ_REL_LONG` | 1345 | -76.17 | 0.8291 | 32.7 | -76.67 |
| `IND-04:VWAP_EXT_UP` | 1878 | -81.80 | 0.8251 | 30.4 | -94.24 |
| `IND-07a:SQZ_REL_SHORT` | 1418 | -81.96 | 0.8208 | 32.7 | -94.57 |
| `IND-04:VWAP_EXT_DN` | 1892 | -89.25 | 0.8232 | 29.4 | -89.84 |

Artifact: `results/runs/2d4064eeea7e9785`

### HYPEUSDT 15m

| family | n | net % | PF ex-cost | win % | max DD % |
|---|---:|---:|---:|---:|---:|
| `IND-06:SWEEP_BEAR` | 136 | -9.62 | 0.8307 | 32.4 | -71.41 |
| `IND-06:SWEEP_BULL` | 161 | -25.90 | 0.6252 | 29.8 | -27.95 |
| `IND-07a:BURST_UP` | 176 | -26.21 | 0.6951 | 29.5 | -28.23 |
| `IND-07a:BURST_DN` | 216 | -30.07 | 0.7463 | 31 | -79.88 |
| `IND-04:VWAP_EXT_DN` | 816 | -43.20 | 0.8638 | 30.5 | -46.62 |
| `IND-07a:SQZ_REL_SHORT` | 558 | -52.69 | 0.7491 | 32.1 | -85.05 |
| `IND-07a:SQZ_REL_LONG` | 557 | -62.44 | 0.6886 | 29.8 | -65.80 |
| `IND-04:VWAP_EXT_UP` | 971 | -69.05 | 0.7999 | 29.7 | -90.90 |

Artifact: `results/runs/17e31ae19837a1ec`

## How the port was proven

| check | result |
|---|---|
| Parity against the ORIGINAL pack (indicator columns at rtol 1e-9, identical signal event sets) | 25 of 25 PASS |
| Known-answer audit of the executor (long and short, target, stop, stop-first tie, gap-through, end-of-data) | 7 of 7 PASS |
| Accounting invariant (equity change equals the sum of net trade PnL) asserted inside every artifact | PASS |

Two defects were found and fixed by these checks, both of which would have produced plausible-looking but wrong numbers:

1. The short's exit was charged `(1-fee)` instead of `(1+fee)`, under-charging every short's buy-back fee. It flattered the short-heavy families; the known-answer audit now covers both directions.
2. The trade PnL did not include fees, so the reported PF was pre-cost while the equity curve was net of costs. A family could then show a PF above one and still lose money. The PF reported here is ex-cost, as the repo's gate requires.

## Conventions (declared, not tuned)

- Signal on the closed bar, fill at the NEXT open.
- The entry bar's own range is after the fill, so target and stop are evaluated on it.
- Stop first on ties; a later bar that gaps through the stop fills at the open.
- One position at a time, no pyramiding, no flip; 1% of cash risked to the frozen stop distance, no leverage.
- Same-bar multi-signal priority: the first event in the pack's own canonical order wins.
- IND-05 (the regime gate) emits no events and is NOT used as a filter: the pack never wires it into the other indicators, and using it as one would be an invention.
- The cost gate runs with the SAME cost regime as the execution, so the gate and the P&L cannot disagree.

## Limits

- **Funding is not charged.** On perps that is a real cost and the source pack has no funding input, so every number here is optimistic for a perp book.
- **LINKUSDT is missing.** It is one of the pack's four scored symbols, but this repo has no 1m, 5m or 15m file for it (only 1h, outside the pack's 1m-30m range). Three of the four scored symbols are measured; the fourth could not be.
- The 1m cells run on the twelve-month window the pack itself declares; the 5m and 15m cells run on the full history in this repo. Each cell's window is in the table above and in its artifact's `inputs`.
- The pack's own OOS window is sealed and was never unsealed; this port does not use it and does not claim to have honoured it, because the port is a different object.


## Superseded artifacts

This campaign produced 24 artifacts from EARLIER engine versions (the port was corrected three times while it was being audited). They stay in the store because `results/runs/` is append-only, and they are NOT citable: `verify` refuses them with an engine drift. Only the 15 artifacts cited above were produced by the current engine.

