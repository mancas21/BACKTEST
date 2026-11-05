# Strategy Generation Prompt — Crypto Perps (Binance USDT-M)

> Copy and paste this entire prompt into any AI model to generate new strategies.

---

## Context and lessons learned (DO NOT ignore)

We have backtested 200+ strategies on Binance perps with rigorous methodology (11-14 bps round-trip costs, real funding, 70/30 IS/OOS split, block bootstrap, walk-forward). Results:

- **Mean reversion** (RSI, Bollinger, VWAP, CCI, Williams %R, etc.): 0/N. All PF < 1.
- **Trend following** (EMA cross, Supertrend, Donchian, MACD, ADX, HMA, Ichimoku): 0/N. Lag kills the edge.
- **Breakout/volatility expansion** (Bollinger squeeze, NR7, range compression): 0/N. False breakouts dominate.
- **Session/event timing** (London open, US cash open, hour-of-day): 0/N. No statistical edge vs costs.
- **Scalping (1m-5m directional)**: 0/10. 7 bps RT vs 23-41 bps ATR per minute = arithmetically impossible for directional trades.
- **Funding carry (directional)**: -76.9%. Funding income (~11%/yr) << price movements (100%+/yr).
- **Funding carry (market-neutral by funding rate)**: -88.8%. Basis risk dominates.
- **Cross-sectional ratios (cointegration)**: 0/15. Unstable in crypto.

## Only validated survivor

**MP-18**: Cross-sectional momentum rotation.
- Ranks 11 crypto perps by 168-bar ROC
- Only considers pairs with 336-bar ROC > 0 (absolute momentum gate)
- Long top-2, short bottom-2, equal weight, rebalance every 336 bars
- Result: +494.7% over 7 years, OOS +49.8%, Sharpe 0.77, DD -66%
- Why it works: it is RELATIVE, not directional. Does not predict price of one asset; ranks assets against each other. Captures cross-sectional momentum factor without market risk.

## Available data (FULL inventory)

### Price data (OHLCV)

| Timeframe | Symbols | Approx bars each | Path |
|-----------|---------|------------------|------|
| **1m** | BTC, ETH, HYPE, SOL, SPX, SUI, XRP | ~2.5M+ | `data/binance_klines_1m/{SYM}_1m.csv` |
| **5m** | BTC, ETH, HYPE, JUP, SOL, SUI, XRP (+ ARB, NVDA, SPCX) | ~500k+ | `data/binance_klines_5m/{SYM}_5m.csv` |
| **5m taker** | BTC, ETH, HYPE, JUP, SOL, SUI, XRP | ~500k+ | `data/binance_klines_5m_taker/{SYM}_5m.csv` (includes taker buy base volume) |
| **15m** | BTC, ETH, HYPE, SOL, SUI, XRP (+ ARB, NVDA, SPCX) | ~170k+ | `data/binance_klines_15m/{SYM}_15m.csv` |
| **1h** | ADA, ARB, AVAX, BNB, BTC, DOGE, ETH, HYPE, JUP, LINK, NEAR, NVDA, SOL, SPCX, SPX, SUI, XRP (+ SOLUSDC) | ~60k+ | `data/binance_klines_1h/{SYM}_1h.csv` |

### Funding data
- 8 symbols: BTC, ETH, HYPE, JUP, SOL, SPX, SUI, XRP
- Files: `data/binance_funding/{SYM}_funding.json`
- Format: `{"t": timestamp_ms, "r": funding_rate}`
- Settlement every 8 hours (00:00, 08:00, 16:00 UTC)

### Taker data (5m)
- Includes `taker_buy_base_vol` column — volume of market buy orders
- This is REAL exchange data, not synthetic
- Useful for order flow / aggressor analysis

### Other data
- AggTrades: `data/aggtrades/` (XRPUSDT imported)
- 1m cache: `data/_1m_cache/`

### Data format (CSV)
Columns: `open_ts, open, high, low, close, volume` (and `taker_buy_base_vol` for taker files)
Timestamps in milliseconds (UTC).

## Rules for new strategies

1. DO NOT generate directional strategies that predict if a single asset goes up or down (unless cross-sectional).
2. DO NOT generate pure mean reversion, pure trend following, pure breakout, or pure session timing.
3. DO NOT generate single-asset strategies.
4. DO generate CROSS-SECTIONAL strategies (comparing assets against each other).
5. DO generate RELATIVE strategies (long/short pairs or baskets).
6. DO generate strategies using information beyond price (funding, taker volume, relative volatility, correlation).
7. Every strategy must be market-neutral or low-beta by construction.
8. Every strategy must have a clear hypothesis of why the edge exists.
9. Every strategy must specify: universe, timeframe, signal, ranking, weights, rebalancing, costs, and why it is not noise.
10. Scalping strategies ARE allowed IF they are cross-sectional or relative (not directional single-asset). The key insight: directional scalping fails (7 bps RT vs 23-41 bps ATR), but cross-sectional scalping (ranking assets by microstructure signals at high frequency) may work.

## Output format

For each strategy, generate:

```
### Strategy N: [Descriptive name]

**Type:** [Cross-sectional / Relative value / Factor / Carry / Volatility / Microstructure proxy / Scalping]

**Timeframe:** [1m / 5m / 15m / 1h / multi-TF]

**Hypothesis:** [Why the edge exists — 1-2 sentences]

**Universe:** [Which assets]

**Signal:** [What is measured, how it is calculated]

**Ranking:** [How assets are sorted]

**Positions:** [Long what, short what, weights]

**Rebalancing:** [Frequency, trigger]

**Estimated costs:** [Expected turnover, bps per rebalance]

**Why not noise:** [Statistical or structural argument]

**Main risk:** [What could kill it]

**Data needed:** [Which files/timeframes]
```

## Categories to explore (generate 2-3 per category)

### A. Cross-sectional factors (beyond momentum) — 1h
- Relative volatility: long low-vol assets, short high-vol (low-vol anomaly)
- Relative liquidity: long assets with higher relative volume, short lower
- Beta: long low-beta-to-BTC assets, short high-beta
- Skewness: long positive-skew assets, short negative-skew
- Autocorrelation: long high-autocorrelation (persistence) assets, short low

### B. Relative value / spread — 1h or 15m
- Ratio z-score between correlated pairs (BTC/ETH, SOL/AVAX, etc.) with entry/exit thresholds
- Volatility convergence: when an asset's vol deviates from its mean relative to BTC
- Relative drawdown: long the asset that fell least, short the one that fell most (during a correction)

### C. Carry / income — 1h
- Funding carry market-neutral: long the pair with most negative funding, short the pair with most positive funding (capture differential, not direction)
- Funding + momentum combo: only enter long when funding < 0 AND momentum positive

### D. Volatility — 1h or 15m
- Volatility risk premium: compare realized vol across assets, long the one with lowest, short highest
- Volatility breakout cross-sectional: long assets whose vol is expanding vs market, short contracting
- Regime: long in low-vol regimes, short in high-vol (cross-sectional)

### E. Microstructure proxies (OHLCV only) — 5m or 15m
- Volume profile: long assets with accumulation (high volume on up-bars), short distribution
- Wick ratio: long assets with long lower wicks (rejection of low prices), short long upper wicks
- Close location: long assets closing in top of range, short bottom of range
- Volume surprise: long assets with unexpectedly high volume, short unexpectedly low

### F. Taker flow (5m taker data) — 5m or 15m
- Taker buy ratio: long assets with highest taker buy ratio, short lowest
- Taker volume momentum: long assets with increasing taker buy volume, short decreasing
- Aggressor imbalance: long assets where buyers are more aggressive, short where sellers are
- Taker flow divergence: price up but taker buy ratio down (weak rally) → short; price down but taker buy ratio up (accumulation) → long

### G. Cross-sectional scalping — 5m or 1m
- High-frequency relative momentum: rank assets by 1h return every 5m, long top, short bottom
- Relative volume spike: long asset with biggest volume spike vs its own history, short smallest
- Cross-asset lead-lag: if BTC moves first, follow with altcoins (or fade)
- Tick-level microstructure: use close location and wick ratios at 5m to rank assets

### H. Combinations / meta-strategies
- Momentum + volatility: rank by Sharpe (return/vol) instead of raw return
- Momentum + funding: only enter long when funding < 0, only short when funding > 0
- Multi-timeframe: combine 5m microstructure + 1h momentum
- Ensemble: average rankings from multiple factors
- Regime-switching: different factor weights in bull vs bear markets

## What we do NOT want

- Strategies that predict direction of a single asset (unless cross-sectional)
- Strategies with more than 5 parameters (overfitting)
- Strategies requiring data we do not have
- Strategies that are not market-neutral or low-beta
- Strategies without a clear hypothesis of why the edge exists
- Pure directional scalping (already proven to fail)

## Generate 20-25 new strategies, prioritizing:
1. Categories A, B, E (OHLCV only, 1h) — most data available
2. Category F (taker flow, 5m) — real order flow data
3. Category G (cross-sectional scalping, 5m) — new territory
4. Categories C, D, H (combinations)

For each, include the format specified above. Be creative but rigorous. Every strategy must be testable with the data we have. Specify the exact timeframe and data files needed.