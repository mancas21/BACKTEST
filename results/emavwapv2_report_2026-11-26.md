# EMA×VWAP Suite 2 (#101–150) — backtest

Date: 2026-11-26. The attachment is a natural-language spec ported to `code/emavwapv2_engine.py` and audited BEFORE any market number (`code/_emavwapv2_audit.py`, 8/8 PASS). The user chose one BTCUSDT pair per row, the same grid as Suite 1. Scope, gates and the 3m resampling are frozen in `results/emavwapv2_pre_registration.md` and its addendum.

## What was run

Forty-eight rows produced a verify-clean artifact. The 3m rows were resampled from the served 1m file by grouping three consecutive bars (a declared derived bar, not an independent download); 5m, 15m and 1h rows use native CSVs. Every artifact computes the unmodified base skeleton on the same slice as its control, charges repo 11 bps RT plus real funding, and asserts the accounting identity. Rows 148 and 149 are NO DATA: their cross-sectional selector book was not implemented with enough fidelity to publish a number.

## Results

| Row | TF | Net % | PF | Trades | Control % | Gates | Verdict | run_id |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 101 | 3m | -100.00 | 0.380 | 11937 | -100.00 | tres de siete | KILLED | `2d2d6143e37ac4e3` |
| 102 | 3m | -92.54 | 0.679 | 6817 | -100.00 | tres de siete | KILLED | `c0cfe501bf0eefea` |
| 103 | 3m | -100.00 | 0.371 | 14106 | -100.00 | dos de siete | KILLED | `5e7e81d78bacc443` |
| 104 | 5m | -8.41 | 0.457 | 194 | 0.11 | dos de siete | KILLED | `13c6f88fdb4b350a` |
| 105 | 5m | -5.16 | 0.738 | 138 | -12.72 | tres de siete | KILLED | `56e740c56377a260` |
| 106 | 5m | -7.32 | 0.641 | 149 | -12.72 | tres de siete | KILLED | `a7fd349ba216d1a4` |
| 107 | 15m | -100.00 | 0.531 | 12066 | -100.00 | dos de siete | KILLED | `3c1dd0be8b9c2c89` |
| 108 | 15m | -100.00 | 0.575 | 9725 | -100.00 | tres de siete | KILLED | `392abe760e78bac7` |
| 109 | 1h | -92.85 | 0.708 | 2506 | -99.65 | tres de siete | KILLED | `e917bae1687e836e` |
| 110 | 3m | -99.99 | 0.411 | 9721 | -100.00 | tres de siete | KILLED | `9ca7890718cfab39` |
| 111 | 3m | -99.91 | 0.450 | 7418 | -100.00 | tres de siete | KILLED | `0157dd42eb435e07` |
| 112 | 3m | -98.11 | 0.507 | 4174 | -100.00 | tres de siete | KILLED | `f25ab3ab53b5ba43` |
| 113 | 5m | -11.27 | 0.491 | 165 | -12.72 | tres de siete | KILLED | `552b52b9fc06b753` |
| 114 | 5m | -0.60 | 0.967 | 121 | -12.72 | tres de siete | KILLED | `7a0f7c193dcd8fa6` |
| 115 | 5m | -12.72 | 0.556 | 227 | -12.72 | dos de siete | KILLED | `60a7762c3cea17b0` |
| 116 | 15m | -99.77 | 0.622 | 5119 | -100.00 | tres de siete | KILLED | `1a49a68921a52d7c` |
| 117 | 15m | 0.00 | - | 0 | -100.00 | uno de siete | NO VERDICT | `2b31baad1a4a2d9f` |
| 118 | 15m | 0.00 | - | 0 | -100.00 | uno de siete | NO VERDICT | `b34c8f55452cc343` |
| 119 | 1h | -38.82 | 0.954 | 1900 | -99.65 | tres de siete | KILLED | `36903148ead60933` |
| 120 | 1h | -99.23 | 0.877 | 6804 | -99.65 | tres de siete | KILLED | `da04af670a0a5baf` |
| 121 | 3m | -99.94 | 0.479 | 7757 | -100.00 | tres de siete | KILLED | `91584cee228201d5` |
| 122 | 5m | -5.81 | 0.586 | 99 | -12.72 | tres de siete | KILLED | `5607148b6df22063` |
| 123 | 15m | -100.00 | 0.613 | 8754 | -100.00 | tres de siete | KILLED | `4a54d19e9b48366b` |
| 124 | 1h | -99.12 | 0.755 | 4764 | -99.65 | tres de siete | KILLED | `4ee302b62b55c76d` |
| 125 | 5m | -6.67 | 0.460 | 83 | -12.72 | tres de siete | KILLED | `028c0106df9c1058` |
| 126 | 15m | -99.75 | 0.651 | 4813 | -100.00 | tres de siete | KILLED | `ddf700986583685a` |
| 127 | 15m | -95.53 | 0.627 | 1916 | -100.00 | tres de siete | KILLED | `d33bbf47639d39a6` |
| 128 | 1h | -72.14 | 0.856 | 1619 | -99.65 | tres de siete | KILLED | `55ea0e23b4d2e3d4` |
| 129 | 3m | -100.00 | 0.406 | 14168 | -100.00 | dos de siete | KILLED | `94293d80cc24d505` |
| 130 | 5m | -32.27 | 0.264 | 376 | -12.72 | dos de siete | KILLED | `f9aaae02313deccc` |
| 131 | 5m | -11.79 | 0.290 | 80 | -12.72 | tres de siete | KILLED | `11e3aa61a4af4f72` |
| 132 | 15m | -100.00 | 0.564 | 11410 | -100.00 | dos de siete | KILLED | `e95307b58717cac8` |
| 133 | 15m | -95.30 | 0.209 | 1656 | -100.00 | tres de siete | KILLED | `0428f97136646f38` |
| 134 | 1h | -80.87 | 0.929 | 1885 | -99.65 | tres de siete | KILLED | `a2c79c076a4bbcad` |
| 135 | 3m | -20.03 | 0.967 | 7144 | -100.00 | tres de siete | KILLED | `a3d4bedc5c4ff7d0` |
| 136 | 3m | -96.33 | 0.651 | 7977 | -100.00 | tres de siete | KILLED | `f05866a1fa00347b` |
| 137 | 5m | -12.74 | 0.513 | 202 | -12.72 | dos de siete | KILLED | `3c0b2713405f1f56` |
| 138 | 5m | 1.93 | 1.147 | 117 | -12.72 | cuatro de siete | KILLED | `fa2624f7f24b86dc` |
| 139 | 15m | -97.24 | 0.580 | 3072 | -100.00 | tres de siete | KILLED | `131800c7c007bb30` |
| 140 | 1h | -97.95 | 0.800 | 4748 | -99.65 | tres de siete | KILLED | `9a9db28ca13b68b1` |
| 141 | 3m | -100.00 | 0.380 | 14915 | -100.00 | dos de siete | KILLED | `60df52cf1f901948` |
| 142 | 3m | -100.00 | 0.369 | 14108 | -100.00 | tres de siete | KILLED | `38d7b9f824af91c9` |
| 143 | 5m | -9.58 | 0.436 | 127 | -12.72 | tres de siete | KILLED | `42e27ec09f2768c3` |
| 144 | 5m | -12.72 | 0.556 | 227 | -12.72 | dos de siete | KILLED | `3db7c853f55f2b21` |
| 145 | 5m | -12.72 | 0.556 | 227 | -12.72 | dos de siete | KILLED | `ef399e5e882989da` |
| 146 | 15m | 3306810.33 | 2.370 | 6145 | -100.00 | siete de siete | QUARANTINED | `deda6dc67d201f07` |
| 147 | 15m | -100.00 | 0.042 | 6066 | -100.00 | dos de siete | KILLED | `984cad641e12e1a8` |
| 150 | 1h | -99.83 | 0.748 | 6088 | -99.65 | dos de siete | KILLED | `2b9f2c5a588f97b0` |

## Verdict

Valid passes: cero. KILLED: 45. NO VERDICT for sample size: dos. QUARANTINED: uno.

The quarantined row is the long-only variant whose mechanical gates are all green but whose net return is astronomical on thousands of trades. That is the arithmetic of full-equity compounding, not a tradable claim: the same rules at the repo's 1%-risk sizing have not been measured, so the row is withheld from any promotion.

Among ordinary rows, the cost-aware gates and selector ideas did cut trade counts, but none turned the base signal into a positive, stable, out-of-sample book. The control itself is deeply negative on the same slices, which is consistent with Suite 1's result and is reported rather than hidden.

## Declared limits

- The 3m bars are derived from 1m; they are not an independent download and are hashed as the served 1m source.
- Reversal/fade rows carry the declared ATR stop and time stop; their gross column is shown next to net so a gross gain erased by costs is not mistaken for edge.
- Higher-timeframe agreement rows use same-chart proxies because a single-pair cell is served only its own bars; they are declared approximations, not the author's exact multi-chart read.
- Limit-fill row 104 counts unfilled orders as missed trades; the measure is inside its artifact, not inferred by the reader.
- These are 50 more trials on top of Suite 1's 50; the deflated Sharpe proxy uses N = 100. Picking a winner after seeing the table would be post-hoc selection, not evidence.

## Provenance

- Pre-registration + addendum: `results/emavwapv2_pre_registration.md`.
- Engine: `code/emavwapv2_engine.py` (uses the audited Suite 1 primitives in `code/emavwap50_engine.py`; both hashes bind each run_id).
- Audit: `code/_emavwapv2_audit.py` 8/8 before the market run.
- Matrix: `results/emavwapv2_matrix.json`.
- Verification log: `results/_emavwapv2_verify.txt`.
