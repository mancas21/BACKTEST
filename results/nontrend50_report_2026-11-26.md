# Non-Trend 50-Strategy Suite (#51–100) — backtest

Date: 2026-11-26. The attachment is a natural-language spec; it was ported to `code/nontrend50_engine.py` and audited BEFORE any market number (`code/_nontrend50_audit.py`, 10/10 PASS). Grid, universes and gates were frozen in `results/nontrend50_pre_registration.md` and its dated addendum. This family is judged only on its own artifacts (REGLA 1).

## What was run

Cross-sectional, dollar-neutral books: ranks at the close, fills at the next open, equal weight per leg, repo 11 bps RT on turnover and funding at real settlements where the universe has funding. Three universes were used: every perp with a native 1h file except the equity/fractional/spot tickers (the spec said seventeen, the repo has more today and the real count is stated per artifact), the seven 5m taker files, and a fixed eight-perp funding universe. Each artifact computes the #51 control on its OWN universe and window, so the correlation to the control is measured inside the artifact.

Thirty-nine rows produced a verify-clean artifact. Eleven are NO DATA: the three overlays not faithfully implemented (declared in the addendum) and the eight composites, which the attachment says may only run from sleeves that cleared the gates on their own — none did.

## Results

| Row | Universe | Net % | PF | Trades | Gates | Control corr | DSR proxy | run_id |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 51 | U (22) | -1.16 | 0.990 | 33 | 1/7 | 1.000 | -2.540 | `eb5820704009e1ce` |
| 52 | U (22) | -2.43 | 0.977 | 32 | 1/7 | 0.279 | -2.623 | `5ee144ba00b9dd3b` |
| 53 | U (22) | -0.79 | 0.996 | 37 | 1/7 | 0.024 | -2.473 | `20a1859383fa0e8d` |
| 54 | U (22) | -2.16 | 0.982 | 37 | 1/7 | 0.082 | -2.595 | `6f0486360c78b7ef` |
| 55 | U (22) | -7.70 | 0.942 | 37 | 1/7 | 0.084 | -2.667 | `bb0dfdbc397daced` |
| 56 | U (22) | -6.50 | 0.967 | 74 | 1/7 | 0.141 | -2.616 | `087ab8fdade0ea70` |
| 57 | U (22) | -6.68 | 0.962 | 33 | 1/7 | 0.350 | -2.531 | `42b86aca0fe70391` |
| 58 | U (22) | 0.99 | 1.005 | 116 | 3/7 | 0.354 | -2.513 | `8352b1e4b619bfa4` |
| 59 | U (22) | -84.72 | 0.974 | 62 | 1/7 | -0.003 | -0.865 | `8b9d86275ffb13c2` |
| 60 | U (22) | -9.64 | 0.913 | 36 | 1/7 | 0.201 | -2.732 | `786342cd3c08ec8e` |
| 61 | U (22) | -0.29 | 0.991 | 33 | 1/7 | 0.992 | -2.748 | `701f25d6ed097eb4` |
| 62 | U (22) | -0.83 | 0.992 | 33 | 1/7 | 0.968 | -2.569 | `a6a5bb607e704a9e` |
| 63 | U (22) | -1.02 | 0.992 | 33 | 1/7 | 0.997 | -2.540 | `3f0b5aa8fe5c731b` |
| 64 | U (22) | -0.11 | 0.999 | 33 | 1/7 | 0.725 | -2.584 | `e607cb71be01cdff` |
| 67 | U (22) | -1.16 | 0.990 | 33 | 1/7 | 1.000 | -2.540 | `52481c7456789352` |
| 69 | T (7) | -32.02 | 0.890 | 502 | 2/7 | 0.014 | -3.535 | `23d1ff3ad037caa2` |
| 70 | T (7) | -10.04 | 0.955 | 237 | 2/7 | 0.003 | -2.859 | `8169b8878d594177` |
| 71 | T (7) | -32.00 | 0.891 | 502 | 2/7 | -0.250 | -3.459 | `b00813891106b633` |
| 72 | T (7) | 1.75 | 1.018 | 18 | 2/7 | 0.073 | -2.454 | `2e9d51623f1cdd7b` |
| 73 | T (7) | -8.39 | 0.954 | 165 | 2/7 | 0.300 | -2.764 | `19d7c678ccf0b593` |
| 74 | T (7) | -6.01 | 0.970 | 158 | 2/7 | -0.118 | -2.697 | `1764e86201beb1ae` |
| 75 | T (7) | -22.69 | 0.908 | 335 | 2/7 | 1.000 | -3.051 | `4c78ad7848069d7f` |
| 76 | T (7) | -32.02 | 0.890 | 502 | 2/7 | 0.014 | -3.535 | `c14751f14ded4e56` |
| 77 | F (8) | -6.98 | 0.940 | 28 | 1/7 | 0.067 | -2.691 | `074dd587c889f36f` |
| 78 | F (8) | -0.92 | 0.989 | 28 | 1/7 | -0.022 | -2.559 | `71bac4ad929d4509` |
| 79 | F (8) | -1.27 | 0.990 | 37 | 1/7 | 0.106 | -2.563 | `f309e76f4ef41aa3` |
| 80 | F (8) | -3.15 | 0.969 | 27 | 1/7 | 1.000 | -2.634 | `9307b3d8ba3426c8` |
| 81 | F (8) | -16.83 | 0.928 | 260 | 2/7 | 0.045 | -3.080 | `d3b59282c1454095` |
| 82 | F (8) | 5.27 | 1.109 | 41 | 2/7 | 0.127 | -2.477 | `263d31e48bd898a1` |
| 83 | U (22) | 7.30 | 1.087 | 36 | 2/7 | -0.150 | -2.382 | `7ef93ad1d47c14d8` |
| 84 | U (22) | -4.75 | 0.966 | 70 | 1/7 | -0.023 | -2.646 | `d96b1e85c10fb661` |
| 85 | U (22) | 5.40 | 1.062 | 35 | 2/7 | -0.136 | -2.414 | `1611e792fe902073` |
| 86 | U (22) | -0.70 | 0.993 | 33 | 1/7 | -0.043 | -2.589 | `30bf89e1d9c5079f` |
| 87 | U (22) | 12.51 | 1.133 | 36 | 2/7 | -0.103 | -2.311 | `a6469a17012f6f7a` |
| 88 | U (22) | 3.43 | 1.036 | 35 | 2/7 | 0.055 | -2.488 | `fda615990b0c3387` |
| 89 | U (22) | -0.45 | 0.996 | 37 | 1/7 | 0.078 | -2.578 | `af22e525abec0e9f` |
| 90 | U (22) | -4.70 | 0.971 | 70 | 1/7 | 0.114 | -2.633 | `6a288c384fb10bed` |
| 91 | U (22) | 4.54 | 1.030 | 35 | 2/7 | 0.225 | -2.438 | `77c3d227c9197073` |
| 92 | U (22) | -8.94 | 0.896 | 35 | 1/7 | 0.052 | -2.822 | `4811b1935c80999b` |

## Verdict

**No row passed the battery.** The best gate count was three of seven, and the highest profit factors stayed near one with tiny trade counts. Several rows have a positive net line but fail the sample, fold, month, bootstrap or drawdown gates; under the frozen rule they are not candidates.

The control itself (#51) does not clear the battery on this window. That is reported as measured, not hidden: every other row is compared against a control that is itself only a reference line, not a validated strategy here.

No composite (#93–100) was run because its source sleeves did not pass on their own, exactly as the attachment requires.

## Declared approximations (read before quoting a number)

- Rows 65, 66 and 68 are NO DATA: the beta-neutral sizing, the per-leg stop with re-entry and the liquidity exclusion were not implemented with enough fidelity to publish a number.
- Rows 58, 59, 72, 73, 75 and 76 are implemented as declared simplifications: a single rebalanced book instead of four offset sleeves, an approximate hold band, a one-sided sign filter, a threshold recomputed from the served bars, and flow/funding filters that gate candidates rather than an exact reimplementation of the author's logic. Their numbers describe what was actually run, not a verbatim reading of every sentence.
- Rows 63, 64 and 67 use exposure-scale overlays computed from the served data; where the trigger never fires the row coincides with #51 on the same universe, which is visible in the table rather than being silently dressed up as a different result.

## Multiple testing

Fifty rows were pre-registered and the deflated-Sharpe proxy uses N = 50 as required. Even so, picking the best of fifty after seeing the results is selection: a positive line among these rows is not evidence on its own. No formal promotion is made from this report.

## Provenance

- Pre-registration + addendum: `results/nontrend50_pre_registration.md`.
- Engine: `code/nontrend50_engine.py` (hashed into every run_id).
- Audit: `code/_nontrend50_audit.py` 10/10 before the market run.
- Matrix: `results/nontrend50_matrix.json` (run_ids, cuts, inputs, gates and the NO DATA ledger).
- Verification log: `results/_nontrend50_verify.txt`.

