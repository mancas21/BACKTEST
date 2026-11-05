# MPS20 -- twenty-strategy multi-pair suite: ported, audited, KILLED

**Deliverable:** runs the requester's twenty-strategy multi-pair suite (the zip "CLAUDE BOT STRATEGIES 1") through the harness. Author code lives in `code/claude_bot_1/` (engine_core.py plus strategies.py); the runner `code/mps20_engine.py` imports it with no byte edits of any computational path and adds only what the harness contract needs (scored regions, strict PF, concentration, zero-cost control drag, benchmark).

**Determinism incident and fix (this session).** The suite's same-bar candidate picking used SETS in three strategies (cross-sectional momentum, RSI rotation, volatility-ranked long-short). Set iteration order in Python depends on the process hash seed, so fill order at the same bar -- and with it the last bits of every float sum over trades (fees, concentration) -- differed between processes. Every artifact produced before the fix verify-REFUSED ("engine non-determinism"), eight of them in this campaign. The fix replaces those candidate sets with the ranked lists they were built from and defines max/min ties to resolve toward the first pair in volatility-ascending rank order. No signal threshold, size, or fee knob changed; the known-answer audit `code/_claude_audit.py` re-ran on the fixed bytes and passed every group. Because `vrun.py verify` re-runs the engine in a fresh process, each verify-OK below is itself the cross-process determinism proof for that artifact.

**Universes.** c5 is the pack's own USDC-literal universe (SOLUSDC/BTCUSDC/ETHUSDC/AVAXUSDC/LINKUSDC) fed with repo USDT 1h prices -- a declared proxy: the USDC/USDT basis at one-hour bars is small relative to the strategies' own thresholds, and this config is the only one in which the two BTC-literal-indexed strategies can trade at all. c4 is the prior four-pair config (BTC/ETH/SOL/XRP as USDT literals), the parity reference, in which those two strategies are structurally dead by their own not-in-data guard.

**Windows.** full scores the entire aligned intersection. last-six-months cuts two thousand four hundred warmup bars plus four thousand three hundred sixty-eight scored bars; every metric in the six-month cells is computed on the scored tail only. The six-month re-basing of short-span EMAs on the warmup segment is negligible at that warmup length and is declared in the engine docstring.

**Costs.** author preset is the suite's shipped fee-plus-slippage per side; repo preset is the standard repo fee-plus-slippage per side. Every artifact additionally carries a zero-cost control pass of the same twenty strategies on the same aligned data and measures the cost drag inside the artifact (the cbpack funding-drag pattern). The report quotes the dragged (costed) numbers everywhere.

**Gate verdicts by cell.**
- c5 full author (`cc33c9473c072c40`): zero of twenty strategies clear every gate.
- c5 full repo (`21c77c89154bddcb`): zero of twenty strategies clear every gate.
- c5 six-month author (`c9153c3c660466d9`): zero of twenty strategies clear every gate.
- c5 six-month repo (`3ce0567eb24132fe`): zero of twenty strategies clear every gate.
- c4 full author (`1692ab92c4ba0442`): zero of twenty strategies clear every gate.
- c4 full repo (`458658ab7289ea1a`): zero of twenty strategies clear every gate.
- c4 six-month author (`f2f34d3891e8c687`): zero of twenty strategies clear every gate.
- c4 six-month repo (`d236d2620866295b`): zero of twenty strategies clear every gate.

## Cell c5 / full / author -- five-pair author universe, full history, author costs

run_id `cc33c9473c072c40`; artifact `results/runs/cc33c9473c072c40.json`. Benchmark (fee-free equal weight across the universe) returns 999.61 percent with a maximum drawdown of -91.78 percent over 53332 scored bars; twenty strategies scored, zero errored. Gate columns: PF is the strict profit factor for discrete strategies and the rebalance-period profit factor for weight mode; G4 (green years) applies to full windows only.

| id | mode | ret pct | gate PF | n | PF half one | PF half two | G4 | beats B&H | conc no top5 | drag pp | fees / gross | verdict |
|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|
| MP01 | discrete | 1641.91 | 1.20 | 957 | 1.15 | 1.21 | pass | yes | -1582.82 | 870.54 | 5.35 | fail |
| MP02 | discrete | 1908.03 | 1.07 | 1341 | 1.24 | 1.04 | fail | yes | -3161.93 | 2748.92 | 6.38 | fail |
| MP03 | discrete | 563.78 | 1.08 | 2044 | 1.08 | 1.09 | pass | no | -216.11 | 1931.56 | 7.09 | fail |
| MP04 | discrete | 11.75 | 1.03 | 507 | 0.71 | 1.41 | pass | no | -92.03 | 36.80 | 5.47 | fail |
| MP05 | discrete | -2.47 | 1.00 | 2071 | 1.01 | 0.99 | fail | no | -203.84 | 167.68 | 6.21 | fail |
| MP06 | discrete | -56.89 | 0.88 | 2536 | 0.90 | 0.85 | fail | no | -83.93 | 62.47 | 11.85 | fail |
| MP07 | discrete | -100.00 | 0.76 | 8471 | 0.76 | 0.66 | fail | no | -112.98 | 0.04 | 7.16 | fail |
| MP08 | discrete | -93.47 | 0.87 | 7624 | 0.89 | 0.80 | fail | no | -111.48 | 89.85 | 11.93 | fail |
| MP09 | discrete | -100.00 | 0.85 | 3016 | 0.85 | 0.74 | fail | no | -142.68 | 0.05 | 5.17 | fail |
| MP10 | discrete | -71.74 | 0.80 | 2698 | 0.79 | 0.83 | fail | no | -82.01 | 33.96 | 10.59 | fail |
| MP11 | discrete | -100.00 | 0.86 | 11788 | 0.86 | 0.80 | fail | no | -116.48 | 8.07 | 10.13 | fail |
| MP12 | discrete | -72.59 | 0.96 | 5655 | 0.96 | 0.96 | fail | no | -124.07 | 2207.12 | 11.12 | fail |
| MP13 | discrete | -30.59 | 0.69 | 177 | 0.76 | 0.65 | fail | no | -58.28 | 4.81 | 7.19 | fail |
| MP14 | discrete | -74.70 | 0.66 | 484 | 0.59 | 0.77 | fail | no | -121.05 | 7.06 | 7.48 | fail |
| MP15 | discrete | 206.17 | 1.03 | 5026 | 1.02 | 1.04 | pass | no | -50.36 | 7255.82 | 9.45 | fail |
| MP16 | weight | 611.99 | 1.13 | 2222 | 1.15 | 1.10 | fail | no | 33.62 | 258.87 | 0.95 | fail |
| MP17 | weight | 6693.12 | 1.26 | 2193 | 1.32 | 1.18 | fail | yes | -1817.73 | 5960.72 | 3.34 | fail |
| MP18 | weight | 146.30 | 1.12 | 2222 | 1.14 | 1.10 | fail | no | 102.50 | 22.95 | 1.13 | fail |
| MP19 | weight | 1254.70 | 1.15 | 2193 | 1.17 | 1.12 | fail | yes | -571.09 | 642.86 | 1.11 | fail |
| MP20 | discrete | 392.21 | 1.04 | 4440 | 1.05 | 1.03 | fail | no | -221.95 | 7284.09 | 8.67 | fail |

Green-year detail (full window): MP01 green in five of seven scored years; MP02 green in four of seven scored years; MP03 green in five of seven scored years; MP04 green in five of seven scored years; MP05 green in three of seven scored years; MP06 green in one of seven scored years; MP07 green in zero of seven scored years; MP08 green in zero of seven scored years; MP09 green in one of seven scored years; MP10 green in zero of seven scored years; MP11 green in zero of seven scored years; MP12 green in two of seven scored years; MP13 green in two of seven scored years; MP14 green in zero of seven scored years; MP15 green in seven of seven scored years; MP16 green in four of seven scored years; MP17 green in four of seven scored years; MP18 green in four of seven scored years; MP19 green in four of seven scored years; MP20 green in four of seven scored years.

## Cell c5 / full / repo6x5 -- five-pair author universe, full history, repo costs

run_id `21c77c89154bddcb`; artifact `results/runs/21c77c89154bddcb.json`. Benchmark (fee-free equal weight across the universe) returns 999.61 percent with a maximum drawdown of -91.78 percent over 53332 scored bars; twenty strategies scored, zero errored. Gate columns: PF is the strict profit factor for discrete strategies and the rebalance-period profit factor for weight mode; G4 (green years) applies to full windows only.

| id | mode | ret pct | gate PF | n | PF half one | PF half two | G4 | beats B&H | conc no top5 | drag pp | fees / gross | verdict |
|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|
| MP01 | discrete | 1231.92 | 1.16 | 958 | 1.14 | 1.16 | pass | yes | -1750.17 | 1280.53 | 6.52 | fail |
| MP02 | discrete | 884.67 | 1.05 | 1340 | 1.22 | 0.99 | fail | no | -1492.03 | 3772.28 | 7.64 | fail |
| MP03 | discrete | 355.63 | 1.06 | 2048 | 1.06 | 1.06 | fail | no | -198.49 | 2139.71 | 8.45 | fail |
| MP04 | discrete | 5.22 | 1.01 | 507 | 0.71 | 1.39 | pass | no | -95.16 | 43.34 | 6.59 | fail |
| MP05 | discrete | -37.31 | 0.98 | 2091 | 0.99 | 0.97 | fail | no | -216.29 | 202.52 | 7.35 | fail |
| MP06 | discrete | -67.32 | 0.85 | 2525 | 0.87 | 0.81 | fail | no | -90.55 | 72.90 | 14.27 | fail |
| MP07 | discrete | -100.00 | 0.74 | 8513 | 0.74 | 0.61 | fail | no | -112.45 | 0.04 | 8.78 | fail |
| MP08 | discrete | -97.23 | 0.84 | 7648 | 0.85 | 0.76 | fail | no | -113.78 | 93.60 | 13.71 | fail |
| MP09 | discrete | -100.00 | 0.85 | 3030 | 0.85 | 0.71 | fail | no | -141.95 | 0.05 | 6.16 | fail |
| MP10 | discrete | -77.72 | 0.77 | 2702 | 0.76 | 0.80 | fail | no | -87.64 | 39.94 | 12.76 | fail |
| MP11 | discrete | -100.00 | 0.84 | 11772 | 0.84 | 0.76 | fail | no | -115.37 | 8.07 | 12.06 | fail |
| MP12 | discrete | -88.56 | 0.94 | 5639 | 0.94 | 0.93 | fail | no | -134.71 | 2223.10 | 12.84 | fail |
| MP13 | discrete | -31.74 | 0.68 | 177 | 0.75 | 0.64 | fail | no | -59.22 | 5.96 | 8.68 | fail |
| MP14 | discrete | -76.03 | 0.65 | 484 | 0.59 | 0.76 | fail | no | -121.83 | 8.39 | 8.98 | fail |
| MP15 | discrete | 26.77 | 1.01 | 5028 | 1.00 | 1.01 | fail | no | -91.84 | 7435.22 | 11.03 | fail |
| MP16 | weight | 533.81 | 1.12 | 2222 | 1.14 | 1.09 | fail | no | -23.67 | 337.06 | 1.23 | fail |
| MP17 | weight | 5262.52 | 1.25 | 2193 | 1.31 | 1.17 | fail | yes | -2026.96 | 7391.32 | 4.14 | fail |
| MP18 | weight | 138.21 | 1.12 | 2222 | 1.13 | 1.10 | fail | no | 95.09 | 31.04 | 1.53 | fail |
| MP19 | weight | 1070.92 | 1.14 | 2193 | 1.17 | 1.11 | fail | yes | -693.08 | 826.63 | 1.43 | fail |
| MP20 | discrete | 102.59 | 1.01 | 4460 | 1.03 | 1.00 | fail | no | -264.76 | 7573.72 | 10.07 | fail |

Green-year detail (full window): MP01 green in five of seven scored years; MP02 green in four of seven scored years; MP03 green in four of seven scored years; MP04 green in five of seven scored years; MP05 green in three of seven scored years; MP06 green in one of seven scored years; MP07 green in zero of seven scored years; MP08 green in zero of seven scored years; MP09 green in one of seven scored years; MP10 green in zero of seven scored years; MP11 green in zero of seven scored years; MP12 green in one of seven scored years; MP13 green in one of seven scored years; MP14 green in zero of seven scored years; MP15 green in four of seven scored years; MP16 green in four of seven scored years; MP17 green in four of seven scored years; MP18 green in four of seven scored years; MP19 green in four of seven scored years; MP20 green in four of seven scored years.

## Cell c5 / last6mo / author -- five-pair author universe, last six months, author costs

run_id `c9153c3c660466d9`; artifact `results/runs/c9153c3c660466d9.json`. Benchmark (fee-free equal weight across the universe) returns 8.19 percent with a maximum drawdown of -34.77 percent over 4368 scored bars; twenty strategies scored, zero errored. Gate columns: PF is the strict profit factor for discrete strategies and the rebalance-period profit factor for weight mode; G4 (green years) applies to full windows only.

| id | mode | ret pct | gate PF | n | PF half one | PF half two | G4 | beats B&H | conc no top5 | drag pp | fees / gross | verdict |
|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|
| MP01 | discrete | 17.81 | 1.51 | 79 | 0.82 | 3.07 | na | yes | -39.29 | 5.12 | 5.12 | fail |
| MP02 | discrete | 8.60 | 1.08 | 126 | 0.44 | 1.46 | na | yes | -45.28 | 12.97 | 8.14 | fail |
| MP03 | discrete | 19.45 | 1.13 | 167 | 0.60 | 1.36 | na | yes | -54.13 | 18.68 | 7.87 | fail |
| MP04 | discrete | -4.02 | 0.92 | 33 | 0.93 | 0.91 | na | no | -25.75 | 2.29 | 9.27 | fail |
| MP05 | discrete | -13.99 | 0.88 | 205 | 0.45 | 1.43 | na | no | -34.38 | 18.63 | 9.79 | fail |
| MP06 | discrete | -4.74 | 0.84 | 187 | 0.93 | 0.74 | na | no | -19.86 | 8.44 | 16.99 | fail |
| MP07 | discrete | -52.25 | 0.81 | 696 | 0.73 | 0.93 | na | no | -30.32 | 32.79 | 14.13 | fail |
| MP08 | discrete | -34.83 | 0.71 | 785 | 0.67 | 0.78 | na | no | -39.38 | 30.56 | 26.83 | fail |
| MP09 | discrete | -37.86 | 0.87 | 222 | 0.61 | 1.24 | na | no | -13.61 | 24.50 | 9.69 | fail |
| MP10 | discrete | -12.30 | 0.79 | 228 | 0.75 | 0.83 | na | no | -24.05 | 8.71 | 15.69 | fail |
| MP11 | discrete | -58.75 | 0.73 | 918 | 0.67 | 0.85 | na | no | -42.19 | 47.13 | 25.58 | fail |
| MP12 | discrete | -10.40 | 0.93 | 425 | 0.67 | 1.15 | na | no | -68.07 | 47.89 | 17.40 | fail |
| MP13 | discrete | -2.88 | 0.64 | 10 | 0.86 | 0.00 | na | no | -5.14 | 0.41 | 7.48 | fail |
| MP14 | discrete | -26.92 | 0.22 | 44 | 0.09 | 0.45 | na | no | -32.09 | 16.25 | 31.69 | fail |
| MP15 | discrete | -22.56 | 0.89 | 410 | 0.64 | 1.12 | na | no | -134.16 | 35.28 | 12.93 | fail |
| MP16 | weight | 5.55 | 1.07 | 182 | 0.78 | 1.49 | na | no | -21.95 | 2.48 | 2.23 | fail |
| MP17 | weight | 11.83 | 1.12 | 182 | 0.60 | 1.42 | na | yes | -38.73 | 5.19 | 4.46 | fail |
| MP18 | weight | 8.05 | 1.14 | 182 | 0.83 | 1.53 | na | no | -7.05 | 2.07 | 4.07 | fail |
| MP19 | weight | 5.57 | 1.07 | 182 | 0.76 | 1.43 | na | no | -41.55 | 4.51 | 3.84 | fail |
| MP20 | discrete | 41.62 | 1.17 | 355 | 0.95 | 1.27 | na | yes | -36.23 | 53.42 | 10.41 | fail |

## Cell c5 / last6mo / repo6x5 -- five-pair author universe, last six months, repo costs

run_id `3ce0567eb24132fe`; artifact `results/runs/3ce0567eb24132fe.json`. Benchmark (fee-free equal weight across the universe) returns 8.19 percent with a maximum drawdown of -34.77 percent over 4368 scored bars; twenty strategies scored, zero errored. Gate columns: PF is the strict profit factor for discrete strategies and the rebalance-period profit factor for weight mode; G4 (green years) applies to full windows only.

| id | mode | ret pct | gate PF | n | PF half one | PF half two | G4 | beats B&H | conc no top5 | drag pp | fees / gross | verdict |
|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|
| MP01 | discrete | 15.09 | 1.46 | 80 | 0.79 | 3.03 | na | yes | -41.13 | 7.83 | 6.26 | fail |
| MP02 | discrete | 6.17 | 1.05 | 126 | 0.43 | 1.43 | na | no | -44.80 | 15.40 | 9.82 | fail |
| MP03 | discrete | 15.75 | 1.10 | 167 | 0.58 | 1.34 | na | yes | -54.21 | 22.38 | 9.51 | fail |
| MP04 | discrete | -4.53 | 0.90 | 33 | 0.91 | 0.89 | na | no | -25.79 | 2.79 | 11.20 | fail |
| MP05 | discrete | -14.87 | 0.87 | 201 | 0.45 | 1.40 | na | no | -33.73 | 19.51 | 11.61 | fail |
| MP06 | discrete | -6.55 | 0.81 | 185 | 0.89 | 0.70 | na | no | -21.37 | 10.24 | 20.95 | fail |
| MP07 | discrete | -59.77 | 0.77 | 698 | 0.71 | 0.88 | na | no | -31.37 | 40.31 | 17.54 | fail |
| MP08 | discrete | -42.52 | 0.64 | 785 | 0.59 | 0.73 | na | no | -43.47 | 38.24 | 33.85 | fail |
| MP09 | discrete | -54.34 | 0.77 | 223 | 0.59 | 1.09 | na | no | -15.43 | 40.99 | 12.64 | fail |
| MP10 | discrete | -14.44 | 0.75 | 228 | 0.71 | 0.79 | na | no | -25.33 | 10.86 | 19.28 | fail |
| MP11 | discrete | -69.20 | 0.66 | 916 | 0.61 | 0.76 | na | no | -42.43 | 57.58 | 32.89 | fail |
| MP12 | discrete | -20.45 | 0.87 | 426 | 0.61 | 1.10 | na | no | -71.28 | 57.94 | 21.62 | fail |
| MP13 | discrete | -2.98 | 0.63 | 10 | 0.84 | 0.00 | na | no | -5.18 | 0.51 | 9.00 | fail |
| MP14 | discrete | -27.41 | 0.22 | 44 | 0.08 | 0.44 | na | no | -31.48 | 16.75 | 38.39 | fail |
| MP15 | discrete | -29.75 | 0.85 | 410 | 0.61 | 1.08 | na | no | -133.90 | 42.47 | 15.82 | fail |
| MP16 | weight | 4.64 | 1.06 | 182 | 0.78 | 1.48 | na | no | -22.33 | 3.39 | 3.05 | fail |
| MP17 | weight | 9.94 | 1.11 | 182 | 0.59 | 1.41 | na | yes | -39.47 | 7.08 | 6.06 | fail |
| MP18 | weight | 7.29 | 1.13 | 182 | 0.82 | 1.51 | na | no | -7.62 | 2.84 | 5.57 | fail |
| MP19 | weight | 3.92 | 1.06 | 182 | 0.75 | 1.43 | na | no | -42.01 | 6.16 | 5.21 | fail |
| MP20 | discrete | 26.46 | 1.11 | 359 | 0.91 | 1.22 | na | yes | -37.57 | 68.58 | 12.78 | fail |

## Cell c4 / full / author -- prior four-pair config, full history, author costs

run_id `1692ab92c4ba0442`; artifact `results/runs/1692ab92c4ba0442.json`. Benchmark (fee-free equal weight across the universe) returns 1139.85 percent with a maximum drawdown of -91.29 percent over 53548 scored bars; twenty strategies scored, zero errored. Gate columns: PF is the strict profit factor for discrete strategies and the rebalance-period profit factor for weight mode; G4 (green years) applies to full windows only.

| id | mode | ret pct | gate PF | n | PF half one | PF half two | G4 | beats B&H | conc no top5 | drag pp | fees / gross | verdict |
|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|
| MP01 | discrete | 1248.63 | 1.13 | 918 | 1.13 | 1.13 | pass | yes | -2017.66 | 1161.80 | 5.93 | fail |
| MP02 | discrete | 1994.29 | 1.13 | 1093 | 1.23 | 1.11 | fail | yes | -3665.82 | 2232.63 | 6.58 | fail |
| MP03 | discrete | 687.87 | 1.15 | 1618 | 1.07 | 1.17 | pass | no | -335.60 | 2025.75 | 7.23 | fail |
| MP04 | discrete | 72.77 | 1.07 | 482 | 1.22 | 0.93 | pass | no | -273.53 | 75.17 | 6.13 | fail |
| MP05 | discrete | 0.00 | - | 0 | - | - | fail | no | - | 0.00 | - | fail |
| MP06 | discrete | -65.98 | 0.85 | 2699 | 0.84 | 0.86 | fail | no | -87.00 | 61.22 | 12.68 | fail |
| MP07 | discrete | -100.00 | 0.69 | 7739 | 0.69 | 0.69 | fail | no | -111.93 | 0.10 | 8.92 | fail |
| MP08 | discrete | -95.86 | 0.82 | 8034 | 0.84 | 0.77 | fail | no | -117.37 | 89.01 | 14.28 | fail |
| MP09 | discrete | -99.99 | 0.84 | 2547 | 0.84 | 0.76 | fail | no | -144.97 | 0.21 | 6.00 | fail |
| MP10 | discrete | 0.00 | - | 0 | - | - | fail | no | - | 0.00 | - | fail |
| MP11 | discrete | -100.00 | 0.81 | 11182 | 0.81 | 0.79 | fail | no | -111.73 | 14.90 | 12.38 | fail |
| MP12 | discrete | -65.52 | 0.97 | 5110 | 0.98 | 0.95 | fail | no | -149.82 | 1750.76 | 11.94 | fail |
| MP13 | discrete | -26.03 | 0.68 | 135 | 0.86 | 0.56 | fail | no | -54.34 | 4.32 | 7.90 | fail |
| MP14 | discrete | 202.57 | 1.22 | 456 | 1.26 | 1.20 | fail | no | -269.89 | 114.83 | 5.28 | fail |
| MP15 | discrete | 174.67 | 1.04 | 4317 | 1.02 | 1.05 | pass | no | -85.35 | 6189.75 | 9.75 | fail |
| MP16 | weight | 964.81 | 1.15 | 2231 | 1.17 | 1.12 | fail | no | 352.70 | 409.57 | 1.41 | fail |
| MP17 | weight | 5464.16 | 1.26 | 2202 | 1.30 | 1.20 | fail | yes | 541.01 | 4428.69 | 4.01 | fail |
| MP18 | weight | 160.68 | 1.13 | 2231 | 1.16 | 1.11 | pass | no | 100.63 | 33.25 | 1.69 | fail |
| MP19 | weight | 3875.78 | 1.19 | 2202 | 1.24 | 1.14 | fail | yes | 742.03 | 1270.54 | 1.29 | fail |
| MP20 | discrete | 340.50 | 1.05 | 3719 | 1.04 | 1.05 | pass | no | -173.16 | 5130.22 | 9.07 | fail |

Green-year detail (full window): MP01 green in five of seven scored years; MP02 green in four of seven scored years; MP03 green in five of seven scored years; MP04 green in five of seven scored years; MP05 green in zero of seven scored years; MP06 green in one of seven scored years; MP07 green in zero of seven scored years; MP08 green in zero of seven scored years; MP09 green in one of seven scored years; MP10 green in zero of seven scored years; MP11 green in zero of seven scored years; MP12 green in one of seven scored years; MP13 green in two of seven scored years; MP14 green in four of seven scored years; MP15 green in five of seven scored years; MP16 green in four of seven scored years; MP17 green in four of seven scored years; MP18 green in five of seven scored years; MP19 green in four of seven scored years; MP20 green in five of seven scored years.

## Cell c4 / full / repo6x5 -- prior four-pair config, full history, repo costs

run_id `458658ab7289ea1a`; artifact `results/runs/458658ab7289ea1a.json`. Benchmark (fee-free equal weight across the universe) returns 1139.85 percent with a maximum drawdown of -91.29 percent over 53548 scored bars; twenty strategies scored, zero errored. Gate columns: PF is the strict profit factor for discrete strategies and the rebalance-period profit factor for weight mode; G4 (green years) applies to full windows only.

| id | mode | ret pct | gate PF | n | PF half one | PF half two | G4 | beats B&H | conc no top5 | drag pp | fees / gross | verdict |
|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|
| MP01 | discrete | 1095.89 | 1.12 | 915 | 1.12 | 1.13 | pass | no | -1900.14 | 1314.53 | 7.01 | fail |
| MP02 | discrete | 904.20 | 1.10 | 1093 | 1.22 | 1.07 | fail | no | -1829.32 | 3322.71 | 7.89 | fail |
| MP03 | discrete | 442.23 | 1.11 | 1623 | 1.06 | 1.14 | pass | no | -328.26 | 2271.38 | 8.64 | fail |
| MP04 | discrete | 27.46 | 1.03 | 482 | 1.16 | 0.88 | pass | no | -293.98 | 120.48 | 7.46 | fail |
| MP05 | discrete | 0.00 | - | 0 | - | - | fail | no | - | 0.00 | - | fail |
| MP06 | discrete | -75.80 | 0.81 | 2700 | 0.80 | 0.82 | fail | no | -94.90 | 71.04 | 15.24 | fail |
| MP07 | discrete | -100.00 | 0.68 | 7767 | 0.68 | 0.66 | fail | no | -111.67 | 0.10 | 10.89 | fail |
| MP08 | discrete | -98.34 | 0.79 | 8048 | 0.80 | 0.72 | fail | no | -116.53 | 91.48 | 16.51 | fail |
| MP09 | discrete | -99.99 | 0.83 | 2558 | 0.84 | 0.73 | fail | no | -144.10 | 0.22 | 7.12 | fail |
| MP10 | discrete | 0.00 | - | 0 | - | - | fail | no | - | 0.00 | - | fail |
| MP11 | discrete | -100.00 | 0.78 | 11150 | 0.78 | 0.74 | fail | no | -110.99 | 14.90 | 14.96 | fail |
| MP12 | discrete | -92.22 | 0.95 | 5110 | 0.96 | 0.90 | fail | no | -160.97 | 1777.46 | 13.42 | fail |
| MP13 | discrete | -27.06 | 0.67 | 135 | 0.85 | 0.55 | fail | no | -55.18 | 5.34 | 9.55 | fail |
| MP14 | discrete | 57.01 | 1.07 | 463 | 1.08 | 1.06 | fail | no | -294.65 | 260.40 | 7.15 | fail |
| MP15 | discrete | 12.92 | 1.00 | 4321 | 1.00 | 1.01 | fail | no | -113.61 | 6351.50 | 11.38 | fail |
| MP16 | weight | 842.45 | 1.14 | 2231 | 1.16 | 1.11 | fail | no | 281.87 | 531.93 | 1.83 | fail |
| MP17 | weight | 4366.19 | 1.25 | 2202 | 1.29 | 1.19 | fail | yes | 154.30 | 5526.67 | 5.01 | fail |
| MP18 | weight | 149.20 | 1.13 | 2231 | 1.15 | 1.10 | fail | no | 90.65 | 44.73 | 2.28 | fail |
| MP19 | weight | 3482.72 | 1.19 | 2202 | 1.24 | 1.13 | fail | yes | 532.95 | 1663.60 | 1.68 | fail |
| MP20 | discrete | 99.74 | 1.02 | 3737 | 1.02 | 1.02 | pass | no | -218.59 | 5370.98 | 10.48 | fail |

Green-year detail (full window): MP01 green in five of seven scored years; MP02 green in four of seven scored years; MP03 green in five of seven scored years; MP04 green in five of seven scored years; MP05 green in zero of seven scored years; MP06 green in zero of seven scored years; MP07 green in zero of seven scored years; MP08 green in zero of seven scored years; MP09 green in one of seven scored years; MP10 green in zero of seven scored years; MP11 green in zero of seven scored years; MP12 green in one of seven scored years; MP13 green in two of seven scored years; MP14 green in three of seven scored years; MP15 green in four of seven scored years; MP16 green in four of seven scored years; MP17 green in four of seven scored years; MP18 green in four of seven scored years; MP19 green in four of seven scored years; MP20 green in five of seven scored years.

## Cell c4 / last6mo / author -- prior four-pair config, last six months, author costs

run_id `f2f34d3891e8c687`; artifact `results/runs/f2f34d3891e8c687.json`. Benchmark (fee-free equal weight across the universe) returns 3.03 percent with a maximum drawdown of -32.16 percent over 4368 scored bars; twenty strategies scored, zero errored. Gate columns: PF is the strict profit factor for discrete strategies and the rebalance-period profit factor for weight mode; G4 (green years) applies to full windows only.

| id | mode | ret pct | gate PF | n | PF half one | PF half two | G4 | beats B&H | conc no top5 | drag pp | fees / gross | verdict |
|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|
| MP01 | discrete | -11.76 | 0.98 | 62 | 0.61 | 1.57 | na | no | -32.46 | 2.31 | 7.71 | fail |
| MP02 | discrete | -15.10 | 0.79 | 91 | 0.35 | 1.04 | na | no | -47.76 | 7.53 | 12.26 | fail |
| MP03 | discrete | 25.03 | 1.20 | 134 | 0.44 | 1.58 | na | yes | -57.94 | 17.39 | 8.14 | fail |
| MP04 | discrete | 3.44 | 1.17 | 32 | 1.02 | 1.33 | na | yes | -23.77 | 2.57 | 7.82 | fail |
| MP05 | discrete | 0.00 | - | 0 | - | - | na | no | - | 0.00 | - | fail |
| MP06 | discrete | -23.86 | 0.64 | 244 | 0.78 | 0.50 | na | no | -31.57 | 13.67 | 21.78 | fail |
| MP07 | discrete | -59.97 | 0.75 | 628 | 0.71 | 0.84 | na | no | -36.98 | 31.79 | 15.76 | fail |
| MP08 | discrete | -41.68 | 0.67 | 899 | 0.65 | 0.69 | na | no | -46.84 | 37.40 | 34.11 | fail |
| MP09 | discrete | -27.39 | 0.90 | 196 | 0.66 | 1.22 | na | no | -15.06 | 27.19 | 10.13 | fail |
| MP10 | discrete | 0.00 | - | 0 | - | - | na | no | - | 0.00 | - | fail |
| MP11 | discrete | -67.58 | 0.67 | 908 | 0.64 | 0.72 | na | no | -45.33 | 48.93 | 30.81 | fail |
| MP12 | discrete | -37.65 | 0.74 | 374 | 0.64 | 0.85 | na | no | -91.14 | 34.88 | 23.42 | fail |
| MP13 | discrete | 2.35 | 1.73 | 6 | 2.61 | 0.00 | na | no | -1.08 | 0.28 | 4.35 | fail |
| MP14 | discrete | -22.86 | 0.37 | 40 | 0.09 | 0.83 | na | no | -32.67 | 18.90 | 19.68 | fail |
| MP15 | discrete | -5.44 | 0.97 | 364 | 0.70 | 1.18 | na | no | -140.93 | 38.70 | 12.50 | fail |
| MP16 | weight | 0.71 | 1.04 | 182 | 0.76 | 1.41 | na | no | -24.22 | 2.12 | 2.20 | fail |
| MP17 | weight | -4.20 | 1.01 | 182 | 0.60 | 1.27 | na | no | -44.07 | 5.09 | 5.08 | fail |
| MP18 | weight | 8.96 | 1.15 | 182 | 0.83 | 1.51 | na | yes | -11.57 | 2.72 | 4.72 | fail |
| MP19 | weight | -4.57 | 1.02 | 182 | 0.69 | 1.42 | na | no | -48.49 | 4.01 | 4.21 | fail |
| MP20 | discrete | 49.53 | 1.21 | 304 | 1.00 | 1.30 | na | yes | -56.62 | 53.85 | 11.04 | fail |

## Cell c4 / last6mo / repo6x5 -- prior four-pair config, last six months, repo costs

run_id `d236d2620866295b`; artifact `results/runs/d236d2620866295b.json`. Benchmark (fee-free equal weight across the universe) returns 3.03 percent with a maximum drawdown of -32.16 percent over 4368 scored bars; twenty strategies scored, zero errored. Gate columns: PF is the strict profit factor for discrete strategies and the rebalance-period profit factor for weight mode; G4 (green years) applies to full windows only.

| id | mode | ret pct | gate PF | n | PF half one | PF half two | G4 | beats B&H | conc no top5 | drag pp | fees / gross | verdict |
|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|
| MP01 | discrete | -12.55 | 0.96 | 62 | 0.60 | 1.54 | na | no | -32.84 | 3.10 | 9.30 | fail |
| MP02 | discrete | -16.66 | 0.77 | 91 | 0.34 | 1.01 | na | no | -48.10 | 9.10 | 14.83 | fail |
| MP03 | discrete | 21.62 | 1.17 | 134 | 0.42 | 1.55 | na | yes | -58.04 | 20.81 | 9.84 | fail |
| MP04 | discrete | 2.87 | 1.15 | 32 | 1.00 | 1.31 | na | no | -23.88 | 3.14 | 9.45 | fail |
| MP05 | discrete | 0.00 | - | 0 | - | - | na | no | - | 0.00 | - | fail |
| MP06 | discrete | -26.14 | 0.61 | 244 | 0.75 | 0.47 | na | no | -33.70 | 15.95 | 26.85 | fail |
| MP07 | discrete | -67.48 | 0.71 | 629 | 0.68 | 0.76 | na | no | -37.08 | 39.30 | 19.80 | fail |
| MP08 | discrete | -50.26 | 0.60 | 903 | 0.58 | 0.62 | na | no | -50.36 | 45.97 | 43.21 | fail |
| MP09 | discrete | -45.33 | 0.81 | 196 | 0.65 | 1.06 | na | no | -17.47 | 45.13 | 13.06 | fail |
| MP10 | discrete | 0.00 | - | 0 | - | - | na | no | - | 0.00 | - | fail |
| MP11 | discrete | -75.46 | 0.61 | 905 | 0.59 | 0.65 | na | no | -43.61 | 56.81 | 39.01 | fail |
| MP12 | discrete | -48.62 | 0.67 | 375 | 0.59 | 0.76 | na | no | -95.93 | 45.85 | 29.77 | fail |
| MP13 | discrete | 2.28 | 1.70 | 6 | 2.56 | 0.00 | na | no | -1.09 | 0.36 | 5.25 | fail |
| MP14 | discrete | -21.73 | 0.37 | 39 | 0.09 | 0.82 | na | no | -30.37 | 17.78 | 23.09 | fail |
| MP15 | discrete | -13.80 | 0.93 | 364 | 0.67 | 1.14 | na | no | -139.30 | 47.07 | 15.25 | fail |
| MP16 | weight | -0.08 | 1.03 | 182 | 0.76 | 1.40 | na | no | -24.52 | 2.91 | 3.01 | fail |
| MP17 | weight | -6.04 | 0.99 | 182 | 0.59 | 1.25 | na | no | -45.16 | 6.94 | 6.89 | fail |
| MP18 | weight | 7.96 | 1.14 | 182 | 0.82 | 1.49 | na | yes | -12.28 | 3.72 | 6.45 | fail |
| MP19 | weight | -6.04 | 1.01 | 182 | 0.68 | 1.41 | na | no | -48.93 | 5.47 | 5.71 | fail |
| MP20 | discrete | 36.26 | 1.16 | 307 | 0.96 | 1.25 | na | yes | -58.18 | 67.12 | 13.50 | fail |

## Cost drag, measured inside the artifacts

Each artifact re-runs the same twenty strategies at zero cost on the same aligned data; drag is that control's return minus the costed return, in percentage points. The largest measured drags in this campaign:

- MP20 (c5 full repo): zero-cost 7676.31 percent versus 102.59 percent costed -- drag 7573.72 points (`21c77c89154bddcb`).
- MP15 (c5 full repo): zero-cost 7461.99 percent versus 26.77 percent costed -- drag 7435.22 points (`21c77c89154bddcb`).
- MP17 (c5 full repo): zero-cost 12653.84 percent versus 5262.52 percent costed -- drag 7391.32 points (`21c77c89154bddcb`).
- MP20 (c5 full author): zero-cost 7676.31 percent versus 392.21 percent costed -- drag 7284.09 points (`cc33c9473c072c40`).
- MP15 (c5 full author): zero-cost 7461.99 percent versus 206.17 percent costed -- drag 7255.82 points (`cc33c9473c072c40`).
- MP15 (c4 full repo): zero-cost 6364.42 percent versus 12.92 percent costed -- drag 6351.50 points (`458658ab7289ea1a`).
- MP15 (c4 full author): zero-cost 6364.42 percent versus 174.67 percent costed -- drag 6189.75 points (`1692ab92c4ba0442`).
- MP17 (c5 full author): zero-cost 12653.84 percent versus 6693.12 percent costed -- drag 5960.72 points (`cc33c9473c072c40`).

Fees as a share of strict gross profit (discrete rows only, where the denominator is defined):

- MP08 (c4 six-month repo): 43.21 percent (`d236d2620866295b`).
- MP11 (c4 six-month repo): 39.01 percent (`d236d2620866295b`).
- MP14 (c5 six-month repo): 38.39 percent (`3ce0567eb24132fe`).
- MP08 (c4 six-month author): 34.11 percent (`f2f34d3891e8c687`).
- MP08 (c5 six-month repo): 33.85 percent (`3ce0567eb24132fe`).
- MP11 (c5 six-month repo): 32.89 percent (`3ce0567eb24132fe`).

## Benchmark

- c5 full author (`cc33c9473c072c40`): equal-weight benchmark return 999.61 percent, benchmark max drawdown -91.78 percent.
- c5 full repo (`21c77c89154bddcb`): equal-weight benchmark return 999.61 percent, benchmark max drawdown -91.78 percent.
- c5 six-month author (`c9153c3c660466d9`): equal-weight benchmark return 8.19 percent, benchmark max drawdown -34.77 percent.
- c5 six-month repo (`3ce0567eb24132fe`): equal-weight benchmark return 8.19 percent, benchmark max drawdown -34.77 percent.
- c4 full author (`1692ab92c4ba0442`): equal-weight benchmark return 1139.85 percent, benchmark max drawdown -91.29 percent.
- c4 full repo (`458658ab7289ea1a`): equal-weight benchmark return 1139.85 percent, benchmark max drawdown -91.29 percent.
- c4 six-month author (`f2f34d3891e8c687`): equal-weight benchmark return 3.03 percent, benchmark max drawdown -32.16 percent.
- c4 six-month repo (`d236d2620866295b`): equal-weight benchmark return 3.03 percent, benchmark max drawdown -32.16 percent.

## Verdict

zero of one hundred sixty strategy-by-cell verdicts clear every pre-declared gate. MPS20 as shipped is KILLED. No further tuning is scheduled; any revival attempt must start from a pre-declared, out-of-sample design, not from re-running this one.
