# The gates, measured: false positives and power (gate calibration)

Artifact `bdb602a549eeecbe` (adapter `gatecal`, engine `code/gatecal_engine.py`, library
`code/gate2.py`, audit `code/_gate2_audit.py`). The v1 gate set G1-G6 had been
adopted by convention; this artifact measures its false-positive rate and its
power, per the audit requirement that a gate set must know its own error rates.

## Construction

- **The null**: random coin-flip entries on real BTCUSDT 1h taker bars
  (17520 bars), filled at the next open by the audited pack50_core
  execution machinery — next-open fills, an intrabar two-ATR stop, a time stop
  sampled per trial from two to seventy-two bars, and funding charged at the
  settlement instants. A null has no edge by construction, so any gate pass is
  a false positive.
- **The planted edge**: the same trials re-scored with a fixed per-trade drift
  of five, ten and twenty bps added to every per-trade return, equity rebuilt
  by compounding. The pass rate against the drift is the power curve.
- **Design**: trade-count targets of thirty, one hundred and three hundred
  crossed with the four drift levels, four hundred trials per cell (twelve
  cells), each trial a distinct generator seeded from the artifact's seed
  (20261027). Costs at the repo gate block (5.0 fee + 0.5 slippage bps
  per side). G9's drawdown null distribution comes from one hundred raw
  mark-to-market curves at the hundred-trade target.
- Both the v1 booleans and the v2 statistical gates (expectancy lower bound,
  purged folds, monthly buckets, top-5% concentration) are scored per trial.

## Results

| n target | planted bps | avg trades | v1 G1 rate | v1 G3 rate | v1 G5 rate | v1 G6 rate | v1 all six | v2 all |
|---|---|---|---|---|---|---|---|---|
| 30 | 0 | 26.0 | 0.1875 | 0.1175 | 0.0125 | 0.0025 | 0.0000 | 0.0000 |
| 30 | 5 | n/a | 0.2650 | 0.1850 | 0.0125 | 0.0050 | 0.0025 | 0.0000 |
| 30 | 10 | n/a | 0.3250 | 0.1975 | 0.0050 | 0.0250 | 0.0025 | 0.0000 |
| 30 | 20 | n/a | 0.4900 | 0.3200 | 0.0150 | 0.0750 | 0.0075 | 0.0000 |
| 100 | 0 | 88.0 | 0.0750 | 0.0875 | 0.0275 | 0.0125 | 0.0025 | 0.0025 |
| 100 | 5 | n/a | 0.1300 | 0.1125 | 0.0175 | 0.0075 | 0.0025 | 0.0000 |
| 100 | 10 | n/a | 0.2150 | 0.2150 | 0.0225 | 0.0475 | 0.0100 | 0.0075 |
| 100 | 20 | n/a | 0.4825 | 0.4600 | 0.0225 | 0.2025 | 0.0175 | 0.0250 |
| 300 | 0 | 273.0 | 0.0075 | 0.0300 | 0.0150 | 0.0025 | 0.0025 | 0.0000 |
| 300 | 5 | n/a | 0.0225 | 0.0800 | 0.0225 | 0.0175 | 0.0100 | 0.0000 |
| 300 | 10 | n/a | 0.0925 | 0.1900 | 0.0125 | 0.0825 | 0.0100 | 0.0025 |
| 300 | 20 | n/a | 0.4975 | 0.5250 | 0.0225 | 0.3950 | 0.0175 | 0.0950 |

- **False positives.** At zero planted edge the v1 all-six conjunction passes
  a null book at a rate of 0.0 to
  0.0025 per cell — small per candidate, but the ledger
  now counts well over a thousand tried candidates, so a surviving book is
  within what this rate produces. The v2 conjunction's null rate at the same
  cells is 0.0 to 0.0025.
- **Power.** Even a twenty-bps-per-trade planted edge clears the v1 all-six
  conjunction only 0.0175 of the time at the three-
  hundred-trade target (0.0075 at thirty trades). The v2
  conjunction is sharper in both directions: a null rate of
  0.0 at zero edge and a pass rate of
  0.095 at twenty bps — roughly five times the power at a
  lower false-positive rate. The individual v1 rates explain why: G1 and G3
  pass nulls often as the edge grows, but G5 (beat buy & hold, against a market
  that returned 24.30% over the window) and G6
  (concentration) are what the conjunction leans on.
- **Drawdown null (G9 context).** A null book's P95 bootstrapped max drawdown
  has median 31.68% and ninetieth percentile
  47.76% of starting capital; the G9v2 cap of
  fifty percent sits above the null's ninetieth percentile, so the cap is a
  tail-risk gate, not a re-skin of ordinary variance.
- **Program-level haircut.** The trial ledger (`results/_trial_ledger.json`,
  recomputed from the append-only run store) counts every artifact as one tried
  candidate; the count is a derived number and is written in words here: the
  store holds twelve hundred and seventy artifacts at the time of writing.
  At the measured per-candidate rates, a handful of false passes across that
  many trials is the expected outcome, so the one surviving book carries this
  program-level haircut on top of its own grid haircut — the forward paper run
  remains the only evidence that settles it.

## Reproduce

    python code/_gate2_audit.py
    python code/_trial_ledger.py
    python code/vrun.py run --strategy gatecal --tf 1h --symbol BTCUSDT --set seed=20261027 --set n_trials=400
    python code/vrun.py verify bdb602a549eeecbe
    python code/vrun.py guard --report results/gate_calibration_report.md
