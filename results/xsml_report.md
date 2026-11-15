# `xsml` — cross-sectional ML book on 1h perps — OOS verdict

- generated: `2026-11-12`
- artifact: `results/runs/d5cefbaf8e3dcb85` (run_id `d5cefbaf8e3dcb85`), reproduces bit-for-bit
- turnover reading: `full` (the frozen spec leaves this open; both readings are reported in `results/xsml_variants_report.md`)
- spec (frozen BEFORE the first market run): `results/xsml_pre_registration.md`
- engine: `code/xsml_engine.py` · adapter `xsml` · features `code/xsml_features.py` (pybroker indicator engine, no backtester) · model `code/xsml_model.py`
- engine audit: `code/_xsml_engine_audit.py` (known answers, both directions) · feature audit: `code/_xsml_feature_audit.py`
- universe: the eight perps with BOTH 1h klines and a real funding file; funding is mandatory on a perp
- costs: 11 bps round trip per leg, charged on entry and exit; **funding charged at the real settlements**, both legs

## Verdict

**KILLED.** The OOS profit factor is below one and the net return is negative. The zero-cost control (measured inside the artifact) shows the book is only marginally positive without costs: the edge per trade does not cover the cost of the turnover, so this is a cost-regime kill on a real-but-weak forecast, not a book that loses money at every price.

| gate | result | measured |
|---|---|---|
| G1 at least one hundred closed trades | PASS | n = 1116 |
| G2 profit factor ex-cost above one point two | FAIL | PF = 0.8969 |
| G3 net return above zero | FAIL | net = -20.75 % |
| G4 commission over gross below thirty per cent | FAIL | commission/gross = - % |
| G5 concentration: without the five best trades the result is still positive | FAIL | net without the five best = -26.03 % |
| G6 thirds: green in two of three | FAIL | 1 of three green (-17.98 / -10.95 / 8.70) |
| G11 a win rate of seventy-five per cent must clear the breakeven win rate by five points | PASS | win rate = 50.2 % |
| KILL out-of-sample profit factor below one | FAIL | PF = 0.8969 |

**2 of 8 gates pass.** The failing ones are the verdict: G2 profit factor ex-cost above one point two, G3 net return above zero, G4 commission over gross below thirty per cent, G5 concentration: without the five best trades the result is still positive, G6 thirds: green in two of three, KILL out-of-sample profit factor below one.

## What the book did

| metric | value |
|---|---:|
| net return (OOS) | -20.75 % |
| profit factor ex-cost | 0.8969 |
| closed trades | 1116 |
| win rate | 50.2 % |
| max drawdown | -29.34 % |
| net WITHOUT costs (control) | 1.16 % |
| cost drag | 21.91 pp |
| fees paid | 1859.74 USDT |
| funding paid (net, real settlements) | -13.78 USDT |
| rebalances | 186 |
| dates not traded (fewer names than the minimum) | 4 |
| exits: stop / target / rebalance / end of data | 502 / 484 / 130 / 0 |
| forecast correlation with the label, on the traded window | 0.1484 (over 35649 rows) |
| accounting invariant residual | 0 |

## Per symbol

| symbol | trades | PF | PnL USDT |
|---|---:|---:|---:|
| ARBUSDT | 150 | 1.0886 | 320.21 |
| BTCUSDT | 138 | 0.6660 | -448.14 |
| ETHUSDT | 125 | 0.8153 | -276.53 |
| HYPEUSDT | 148 | 0.8991 | -322.39 |
| JUPUSDT | 149 | 0.8881 | -426.02 |
| SOLUSDT | 133 | 0.8729 | -249.27 |
| SUIUSDT | 145 | 0.7917 | -661.79 |
| XRPUSDT | 128 | 0.9853 | -24.61 |

## How to read this

- **The forecast does correlate out of sample** (the artifact measures it on the traded window), and the book still loses. A weak rank is not a tradeable edge: the stop truncates the outcome the label was measuring, and the cross-sectional spread does not cover the eleven basis points per leg that each turnover pays.
- **The zero-cost control is positive but marginal (1.16 %)**, so this kill is about the cost regime meeting a weak signal, not about a book that has no signal at all.
- Judged on its own artifacts (REGLA 1). No other book in this repo is evidence about this one.

## Declared limits

- The window is short: the study starts when the sixth name has both klines and funding, and the OOS is a few months.
- The model was fitted ONCE on DEV; there is no grid and no model selection, so there is no trial count to discount — but there is also no ensemble, and no robustness check across feature subsets (that would have been new trials, and the spec forbids them).
- The label is a one-day forward return; the book realizes a stop-and-target outcome on a stop twice the ATR, so the label and the realized PnL are different objects. That mismatch is part of what the numbers show, and it was declared in the spec.
- Leg sizes are frozen at the initial equity: the book does not scale its notional as equity moves.
- No margin or liquidation model: the gross exposure cannot breach the declared cap, but no collateral check is made.
- This is a paper measurement on the repo's klines. No orders were placed.

## Reproduction

```
python code/vrun.py run --strategy xsml --tf 1h --symbol XSML8 --params '{"split": "OOS", "turnover": "full"}'
python code/vrun.py verify d5cefbaf8e3dcb85
python code/_xsml_engine_audit.py
```

The features and the model are upstream of the artifact and are reproduced by:

```
& "$HOME\.venvs\pybroker\Scripts\python.exe" code/xsml_features.py
& "$HOME\.venvs\pybroker\Scripts\python.exe" code/_xsml_feature_audit.py
& "$HOME\.venvs\pybroker\Scripts\python.exe" code/xsml_model.py --variant v1
```

