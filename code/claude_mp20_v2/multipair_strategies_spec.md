# Multi-Pair Crypto Strategy Suite — 20 Strategies, Specification & Backtest Framework

## Status of this deliverable — read this first

**No real backtest numbers are in this document.** This sandbox has no network path to
Binance or any exchange API (its egress is locked to package registries — PyPI, npm,
GitHub — not market-data hosts), so there is no way for me to pull genuine 6-month 1h
OHLCV data here. Rather than invent Sharpe ratios and equity curves that *look* like a
real backtest, this deliverable is split into what's real right now and what needs your
data to become real:

1. **Real, done now:** full specs for all 20 strategies below, and a complete,
   execution-tested Python backtesting engine (`engine_core.py`, `strategies.py`,
   `run_backtest_suite.py`) implementing every rule exactly as written.
2. **Validated, not real performance:** I ran the full 20-strategy suite against
   synthetic price paths (correlated GBM + noise, *not* real market data) purely to prove
   the code runs end-to-end, handles all 20 strategies without errors, and produces the
   requested outputs (ranked metrics table, per-strategy equity + drawdown charts). Those
   files are named `synthetic_smoketest_*` — treat every number in them as a code-correctness
   check, not a trading signal.
3. **Pending your data:** point `run_backtest_suite.py` at real 1h OHLCV CSVs (schema
   below) and it produces the actual 20-strategy comparison, ranked by Sharpe, with real
   equity curves and drawdowns. See "How to get real numbers" at the end.

---

## Common framework

- **Universe:** `SOLUSDC, BTCUSDC, ETHUSDC, AVAXUSDC, LINKUSDC` (swap in `strategies.py` /
  `UNIVERSE` if you'd rather run this on your usual XRP/SUI/SOL/BTC perp set).
- **Timeframe:** 1h candles, 6-month window (~4,380 bars).
- **Costs:** 0.05% taker fee per fill, per side; 3 bps slippage per fill (both
  configurable in `engine_core.py`).
- **Starting equity:** $100,000, same for every strategy and the benchmark.
- **Benchmark:** equal-weight buy-and-hold across the same universe, same start date.
- **Two execution modes**, both producing a common equity curve for comparison:
  - **discrete** — event-driven, ATR(14)×multiplier stop-loss per leg, position size =
    (equity × risk%) ÷ stop distance. Covers archetypes 1–3 and the pairs/spread
    strategies.
  - **weight** — continuous target-weight rebalancing, turnover-based fees, optional
    gross-leverage cap. Covers the risk-parity/rotation archetype.
- **Metrics:** cumulative return vs. benchmark, Sharpe & Sortino (annualized off 1h bars,
  24/7 crypto — factor √8760), max drawdown, win rate, total trades (or rebalance
  periods for weight-mode strategies), profit factor, expectancy in R-multiples (or mean
  period return for weight-mode).

### Known modeling simplifications (deliberate, documented — not hidden)
- Pairs/spread strategies (06, 08, 10) split total spread risk 50/50 between the two legs
  rather than sizing strictly by the OLS hedge ratio. The hedge ratio *is* used to build
  the spread and its z-score — just not for exact per-leg dollar weighting.
- "Cointegration ranking" (06) is proxied by the lowest rolling OLS-residual variance
  among candidate pairs, not a formal Engle-Granger/ADF test. Swap in
  `statsmodels.tsa.stattools.coint` if you want the formal version.
- Squeeze/regime percentile filters (12, 13) use rolling min-max normalization instead of
  a true percentile rank, for speed. Directionally equivalent, less precise at the tails.
- Weight-mode "trades" for win-rate/profit-factor/expectancy are per-rebalance-period P&L
  — there's no round-trip concept in a continuously rebalanced allocation.

---

## Archetype 1 — Multi-Pair Trend-Following / Momentum

### MP-STRAT-01: Cross-Sectional Momentum & Rotation
- **Universe/selection:** rank all 5 pairs by 30-day (720-bar) trailing return; hold the
  top 2, rebalanced every 24h.
- **Entry:** enter long any pair that enters the top-2 rank at a rebalance bar.
- **Exit:** close a leg the moment its pair drops out of the top-2 at a rebalance bar
  (early exit also triggers on ATR stop, see sizing).
- **Sizing/risk:** 1% equity risk per leg, ATR(14)×2 stop, max 2 concurrent legs, 2%
  portfolio heat cap.

### MP-STRAT-02: Dual Moving-Average Trend Filter Basket
- **Universe/selection:** all 5 pairs, evaluated independently every bar.
- **Entry:** EMA(20) crosses above EMA(100) **and** close > EMA(200) (regime filter).
- **Exit:** EMA(20) crosses back below EMA(100), or ATR stop.
- **Sizing/risk:** 1% risk/trade, ATR(14)×2 stop, up to 5 concurrent legs, 5% heat cap.

### MP-STRAT-03: Donchian Breakout Multi-Asset (Turtle-style)
- **Universe/selection:** all 5 pairs, independently evaluated.
- **Entry:** close breaks above the prior 55-bar high.
- **Exit:** close breaks below the prior 20-bar low, or ATR stop.
- **Sizing/risk:** 1% risk/trade, ATR(14)×2 stop, up to 5 concurrent, 5% heat cap.

### MP-STRAT-04: MACD Histogram Momentum Rank & Rotate
- **Universe/selection:** rank all 5 by the slope of MACD histogram over the trailing 6
  bars; hold the top 3 with positive slope, rebalanced weekly (168 bars).
- **Entry:** a pair enters the top-3 positive-slope rank at a weekly rebalance.
- **Exit:** drops out of the top-3 (or negative slope) at rebalance, or ATR stop.
- **Sizing/risk:** base 1% risk/trade, scaled by inverse 20-bar realized vol
  (normalized across the selected 3, clipped to 0.3×–2.0×), ATR(14)×2 stop, max 3
  concurrent, 4.5% heat cap.

### MP-STRAT-05: Relative Strength vs. BTC Trend-Following
- **Universe/selection:** the 4 non-BTC pairs, ranked by their price/BTC ratio trend.
- **Entry:** ratio EMA(20) > ratio EMA(50) (alt outperforming BTC on a rolling basis),
  checked every 12h, max 3 concurrent.
- **Exit:** ratio EMA(20) crosses back below EMA(50), or ATR stop.
- **Sizing/risk:** 1% risk/trade, ATR(14)×2 stop, 3% heat cap.

---

## Archetype 2 — Statistical Arbitrage & Pairs / Basket Mean-Reversion

### MP-STRAT-06: Cointegrated Pairs Spread Trading
- **Universe/selection:** every 7 days, scan all 10 pair combinations in the universe;
  select the pair with the lowest 90-day rolling OLS-residual variance on log-prices
  (cointegration-strength proxy) and its hedge ratio (β).
- **Entry:** z-score of the log-price spread (window 50) < −2 → long A / short B; > +2 →
  short A / long B.
- **Exit:** |z| reverts below 0.3 (converged) or blows out past 3.5 (structural-break
  stop).
- **Sizing/risk:** 1% total risk on the spread, split 50/50 across the two legs, each
  leg's own ATR(14)×2 as its stop distance, 1% heat cap (single spread position at a
  time).

### MP-STRAT-07: Cross-Asset Z-Score Basket Mean Reversion
- **Universe/selection:** all 5 pairs, evaluated independently — no pairing.
- **Entry:** z-score of price vs. its own 50-bar mean < −2 → long; > +2 → short.
- **Exit:** z-score reverts through 0, or ATR stop.
- **Sizing/risk:** 1% risk/trade, ATR(14)×2 stop, up to 4 concurrent legs, 4% heat cap.

### MP-STRAT-08: Basket-Neutral Mean Reversion (Laggard / Leader)
- **Universe/selection:** daily, compute each pair's 50-bar return minus the equal-weight
  basket's average 50-bar return; the biggest negative deviation is the laggard, the
  biggest positive is the leader.
- **Entry:** long laggard / short leader as soon as the pairing changes and no position
  is open.
- **Exit:** the laggard/leader deviation spread converges below 0.5 percentage points.
- **Sizing/risk:** 1% total risk, split 50/50 across the two legs, 1% heat cap.

### MP-STRAT-09: Volatility-Weighted Multi-Pair RSI Reversion
- **Universe/selection:** all 5 pairs simultaneously, no rotation.
- **Entry:** RSI(14) < 30, position scaled by inverse 20-bar realized vol (clipped
  0.3×–3.0× base risk) so lower-vol pairs get proportionally larger size.
- **Exit:** RSI(14) > 70, or ATR stop.
- **Sizing/risk:** base 1% risk/trade (vol-scaled), ATR(14)×2 stop, up to 5 concurrent,
  8% heat cap (wider, since vol-scaling can push individual legs above the 1% base).

### MP-STRAT-10: Triangular Basket Spread Reversion (SOL/ETH via BTC ratio)
- **Universe/selection:** fixed SOL vs. ETH — the BTC terms in a SOL/BTC vs. ETH/BTC
  ratio-spread cancel algebraically, so this reduces to a direct SOL/ETH log-price
  spread; rolling hedge ratio (β) over a 100-bar window.
- **Entry:** z-score of the spread < −2 → long SOL / short ETH; > +2 → the reverse.
- **Exit:** |z| < 0.5 (converged) or > 3.5 (stop-out).
- **Sizing/risk:** 1% total risk, 50/50 split, 1% heat cap.

---

## Archetype 3 — Volatility & Relative Strength

### MP-STRAT-11: Multi-Pair RSI Ranking Rotation
- **Universe/selection:** rank all 5 by RSI(14) ascending every 4h; hold the bottom 2
  (most oversold).
- **Entry:** a pair enters the bottom-2 rank at a 4h rebalance.
- **Exit:** drops out of bottom-2 at rebalance, **or** RSI(14) > 60 at any time
  (checked every bar, not just rebalances).
- **Sizing/risk:** 1% risk/trade, ATR(14)×2 stop, max 2 concurrent, 2% heat cap.

### MP-STRAT-12: Bollinger Band-Width Squeeze Breakout
- **Universe/selection:** all 5 pairs; "squeeze" = bandwidth in the bottom ~20% of its
  trailing 100-bar range (normalized min-max proxy).
- **Entry:** on the bar after a squeeze, close breaks above the upper band (long) or
  below the lower band (short).
- **Exit:** close crosses back through the middle band, or ATR stop.
- **Sizing/risk:** 1% risk/trade, ATR(14)×2 stop, up to 3 concurrent, 3% heat cap.

### MP-STRAT-13: ATR-Percentile Volatility Regime Filter Momentum
- **Universe/selection:** all 5 pairs; same EMA(20)/EMA(50) cross as a trend signal, but
  gated to only fire when ATR% (ATR/price) is in the top half of its trailing 60-day
  range — skips "dead" low-vol pairs.
- **Entry:** EMA(20) crosses above EMA(50) **and** ATR-percentile filter is active.
- **Exit:** EMA(20) crosses back below EMA(50), or ATR stop.
- **Sizing/risk:** 1% risk/trade, ATR(14)×2 stop, up to 5 concurrent, 5% heat cap.

### MP-STRAT-14: Realized-Vol Ranked Long/Short Relative Strength
- **Universe/selection:** weekly, rank all 5 by 20-bar realized vol into terciles; take
  the best-momentum pair in the high-vol tercile long, and the worst-momentum pair in the
  low-vol tercile short.
- **Entry:** at the weekly rebalance, per the rule above.
- **Exit:** drops out of its role at the next rebalance, or ATR stop.
- **Sizing/risk:** 1% risk/trade, ATR(14)×2 stop, max 2 concurrent (one long, one
  short), 2% heat cap.

### MP-STRAT-15: Multi-Pair Keltner Channel Volatility Breakout
- **Universe/selection:** all 5 pairs.
- **Entry:** close breaks above the upper Keltner band (long) or below the lower band
  (short).
- **Exit:** close crosses back through the mid-line (EMA20), or ATR stop.
- **Sizing/risk:** 1% risk/trade, ATR(14)×2 stop, up to 4 concurrent, 4% heat cap.

---

## Archetype 4 — Multi-Asset Risk-Parity & Dynamic Rotation

### MP-STRAT-16: Inverse-Volatility Risk Parity Static Basket
- **Universe/selection:** all 5 pairs, always held (no exits) — weights only.
- **Entry/exit:** none in the discrete sense; daily reweighting to inverse-20-bar-vol
  targets (lower-vol pairs get more capital, for equal risk contribution).
- **Sizing/risk:** gross exposure capped at 1.0× equity (unlevered).

### MP-STRAT-17: Trend-Confirmed Dynamic Rotation (Dual Momentum)
- **Universe/selection:** daily, blend 12h/72h/30d momentum per pair; only pairs with
  **positive** blended momentum qualify (else the book goes to cash).
- **Entry/exit:** hold the top-2 qualifying pairs equal-weighted; anything not
  qualifying (or not top-2) is unwound at the daily rebalance.
- **Sizing/risk:** gross exposure capped at 1.0× equity.

### MP-STRAT-18: Target-Volatility Portfolio Overlay
- **Universe/selection:** equal-weight basket of all 5, daily leverage adjustment.
- **Entry/exit:** none discretely; the overlay scales total exposure to target a 15%
  annualized realized-vol, leverage clipped to [0.25×, 3.0×].
- **Sizing/risk:** gross exposure capped at 3.0× equity.

### MP-STRAT-19: Correlation-Adjusted Momentum Rotation
- **Universe/selection:** daily, rank by 30-day momentum; build a top-3 basket but skip
  any candidate whose 30-day return correlation with an already-selected pair exceeds
  0.8, favoring diversification over pure momentum rank.
- **Entry/exit:** equal-weight the selected basket; drop and replace at each daily
  rebalance.
- **Sizing/risk:** gross exposure capped at 1.0× equity.

### MP-STRAT-20: Regime-Switching Trend/Mean-Reversion Rotation
- **Universe/selection:** all 5 pairs, each independently classified by ADX(14) every
  bar: > 25 → trend mode, < 20 → reversion mode, 20–25 → hold prior mode (hysteresis
  band, avoids whipsaw at the threshold).
- **Entry:** trend mode → EMA(20) > EMA(50); reversion mode → RSI(14) < 30.
- **Exit:** trend mode → EMA(20) < EMA(50); reversion mode → RSI(14) > 60; either mode,
  ATR stop applies.
- **Sizing/risk:** 1% risk/trade, ATR(14)×2 stop, up to 5 concurrent, 5% heat cap.

---

## Engine files delivered

- **`engine_core.py`** — indicator library (RSI, ATR, EMA, MACD, Bollinger, Keltner,
  Donchian, ADX, realized vol, z-score), the discrete and weight-based portfolio
  simulators (fees, slippage, ATR stops, heat caps, leverage caps), metrics, and
  plotting.
- **`strategies.py`** — all 20 signal/weight functions above, wired into a
  `StrategyConfig` registry (`build_strategies()`).
- **`run_backtest_suite.py`** — the CLI entry point: loads data, runs all 20, writes a
  Sharpe-ranked summary CSV and one equity+drawdown chart per strategy.

## How to get real numbers

`run_backtest_suite.py` expects one CSV per pair, named exactly `<PAIR>.csv` (e.g.
`SOLUSDC.csv`), columns `timestamp, open, high, low, close, volume` (timestamp as
UTC ISO8601 or epoch ms/s; 1h candles, ascending). Given your existing ccxt-based data
layer, the fastest path is almost certainly a short local script using `ccxt`'s
`fetch_ohlcv` (paginated, since Binance caps ~1000–1500 candles per call) to dump the
last 6 months of 1h candles per pair to that schema — happy to write that puller script
if useful. Then:

```bash
python run_backtest_suite.py --data-dir ./data --out-dir ./results
```

produces `results/summary_ranked_by_sharpe.csv` (the real master comparison table) and
`results/MP-STRAT-XX_equity_drawdown.png` for all 20 — at that point the top-3
risk-adjusted breakdown you asked for at the end can be written for real, against your
actual data and regime, instead of a synthetic placeholder.

## Synthetic smoke-test results (engine validation only — NOT real performance)

`synthetic_smoketest_summary.csv` and the four sample charts
(`synthetic_smoketest_chart_*.png`, one per archetype) came from a correlated-GBM
synthetic universe with a strong built-in sinusoidal trend regime — which is exactly why
the trend/momentum strategies "won" and the mean-reversion ones "lost" in that run. That
pattern is an artifact of the synthetic generator, not a market finding, and will not
carry over to real data. Its only purpose is proving every one of the 20 strategies
executes cleanly end-to-end and produces well-formed output.
