# Trend Magic Enhanced (AlgoAlpha, Pine v5) - audit, rewrite, port

Files: `trend_magic.pine` (v6) · `tm_core.py` (indicator, `fixed` + `legacy`) · `tm_backtest.py` (engine, sweep, DSR, walk-forward) · `tm_data.py` · `test_tm.py` (20 tests)

## 1. Findings in the original

| # | Severity | Finding | Effect | Fix |
|---|---|---|---|---|
| 1 | High | **Zero seed.** `nz(magicTrend[1])` = 0 on the first bar. Bearish branch is `trendDown > prev ? prev : trendDown`; with prev = 0, `trendDown > 0` is always true, so the line stays at **0** until CCI turns >= 0. | No line, `trendDirection` stays 0 (neither `crossover(low, 0)` nor `crossunder(high, 0)` can fire), no signals - from the first valid bar until CCI first turns >= 0. Hits the *start* of every series; matters on short backtest windows that begin in a down-leg. Self-heals if the first valid CCI >= 0. | Seed on first valid bar (`trendUp` / `trendDown` by regime). |
| 2 | High | **CCI na -> bearish branch.** For the first `cciPeriod-1` bars (and any flat window, dev = 0) `cci >= 0` is false, so the else (bearish) branch runs. | Warm-up bars are silently treated as bearish and feed finding 1. | Regime *holds* when CCI is na; state is not updated before the first valid bar. |
| 3 | High (smoothing on) | **Smoothing feeds back into the ratchet.** `nz(magicTrend[1])` reads the previous bar's *final* value, i.e. after `magicTrend := smoothMagicTrend ? ma(...) : magicTrend`. | By my reading of the source the ratchet is fed its own MA output: the floor/ceiling is a lagged average, not the running max/min, so it no longer ratchets and results depend on MA type/length in a way that is not "smoothing a line". Default is off, so only sweeps with Smooth = true are affected. | Ratchet state is raw and never smoothed; smoothing only produces the *trigger/plot line*. |
| 4 | High (live) | **Repaint / lookahead.** Flips use the current bar's low/high and the current ATR/CCI. On the realtime bar they can appear and vanish; `alertcondition` fires per tick unless set to once-per-bar-close. | A flip is only knowable at the close. A backtest that fills on the same bar overstates results. | Signals gated on `barstate.isconfirmed`; Python fills at the **next open**, `delay >= 1` enforced. |
| 5 | Low | `ta.lowest(21)` / `ta.highest(21)` marker offset hard-coded; `input(close)` instead of `input.source`; `ta.*` calls inside ternary/`switch` (v6 evaluates lazily -> inconsistent history risk). | Cosmetic / v6 hygiene. | Markers use `location.belowbar/abovebar`; all MAs/ATRs computed every bar, selected afterwards. |

## 2. Behaviours that are by design (not bugs), but matter for trading

- **Line freeze.** After CCI flips against the side the line is on, the line stays flat at its old level until price touches it. Distance price-to-line is unbounded, so ATR/line-based position sizing is invalid on this indicator. A re-anchor clamp (e.g. cap distance at k x ATR) is the obvious next experiment; not added because it changes the model.
- ATR is `SMA(TR)`, not Wilder. This matches classic Trend Magic; `RMA(TR)` exposed as an option. Default multiplier 2.0 differs from the classic 1.0.
- Wick flips: `low` crossing above the line is satisfied by a bar that then closes anywhere. `flip_on="close"` is the less noisy alternative.
- Direction initialises from price vs line on the first valid bar (original starts at 0 and waits for a cross). No signal is emitted at initialisation; the backtester only trades genuine flips.

## 3. What is and is not verified

Verified (20 tests, all pass):
- Primitives (SMA/EMA/RMA/WMA/VWMA/TR/CCI) equal naive loop references.
- Causality: truncating the data or perturbing the future leaves all outputs <= k unchanged (all engines, all MA types).
- Ratchet monotone within a regime; smoothing never changes the state; no NaN / zero line after warm-up.
- Findings 1 and 2 are reproduced by `mode="legacy"`; `legacy` and `fixed` agree exactly once the original has produced its first signal (when the first CCI >= 0).
- Accounting: flat book = flat equity; always-long = close_last / open_1; closed-form round trip with costs; per-trade log-returns sum to log(equity) exactly (flip, leverage, delay variants).
- Statistics: expected-max-Sharpe matches Monte Carlo; DSR flags best-of-96 on a driftless martingale as non-significant and detects a planted trend; zero-cost null over random-walk seeds has mean Sharpe ~0 while a deliberate 1-bar peek gives ~+3.

NOT verified:
- `trend_magic.pine` was **not compiled** (no TradingView here). Constructs are conservative; paste it into the editor and fix anything the compiler flags.
- No parity check against real TradingView output. To do it: export the original indicator's plotted values (and OHLCV) from TradingView for a symbol, run `trend_magic(df, mode="legacy")`, diff `raw`/`dir`. Expect agreement from the first valid bar if `smooth=false`.
- `smooth=true`: not emulated in `legacy` (finding 3 relies on reading the source; window semantics of `ta.*` on a re-assigned variable inside a user function can't be verified offline). The `fixed` smoothing path (EMA/RMA seeding on a series with leading na) follows Pine's documented seeding but is untested against TradingView.
- `fetch_binance_klines` is untested (sandbox network is allow-listed).
- No real-market results were produced - only synthetic data, used for mechanics.

## 4. Backtest design and limits

- Fill at open of bar t+delay; stop-and-reverse; position in {-1, 0, +1} x leverage, rebalanced to constant leverage every bar.
- Costs: `fee_bps + slip_bps` per side on traded notional (defaults 5 + 2, Binance USDT-M taker VIP0 + a modest slippage guess; set your real numbers). A flip pays both legs.
- Not modelled: liquidation/margin (keep leverage <= ~3), funding (pass a per-bar series to `run_backtest(funding=...)`), partial fills, order-book impact.
- Sweep -> `deflated_sharpe` (Bailey & Lopez de Prado) with N = number of configs tried. Configs are strongly correlated (e.g. `cci_len` barely changes results), so N overstates the effective trials: conservative. DSR assumes roughly iid bars; serial correlation makes it optimistic.
- `walk_forward` picks the best train-Sharpe config per window and stitches the next test window. Valid because the indicator and engine are causal; switching cost between configs is ignored.
- Memory: the sweep keeps one float64 return column per config (bars x configs).

## 5. Usage

```bash
pip install numpy pandas scipy
python test_tm.py                                   # or: python -m pytest -q test_tm.py
python tm_backtest.py --csv SOLUSDT_1h.csv --sweep  # time + open/high/low/close/volume
python tm_backtest.py --synthetic --sweep           # mechanics only; --trend-strength 0.08 plants an edge
```

```python
from tm_core import TMParams, trend_magic
from tm_backtest import BTConfig, run_backtest, perf, periods_per_year
tm  = trend_magic(df, TMParams(cci_len=20, atr_len=5, atr_mult=2.0))          # mode="fixed"
res = run_backtest(df, tm["sig"].to_numpy(), BTConfig(fee_bps=5, slip_bps=2))
print(perf(res.ret, periods_per_year(df.index), res.pos, res.trades))
```
