# STRATEGY GENERATOR SUPER-PROMPT (v2.0, 2026-11-20)

## BEFORE USE (operator only; do not paste this block)

1. Fill or confirm the DATA INVENTORY in section 1. Fields left as `<...>` fall back to the v1 minimum (7 symbols, ~2 years). If the 1h set covers more symbols or more history, fill it in: breadth and history length are the biggest levers in this prompt.
2. Confirm the EXECUTION CONTRACT (section 2) matches the engine. Items marked [VERIFY ENGINE] are assumptions.
3. Confirm engine capabilities: multi-asset baskets, resting-limit simulation, walk-forward ML refit hook, trade-counting convention for baskets, portfolio-level gate. Delete the archetypes the engine cannot run.
4. The output is now a strict YAML spec (section 7), not the v1 prose format. If the ingest still parses v1 text, use "Compatibility mode" at the end of section 7.
5. Paste everything below the line into any LLM.

---

You are a systematic-strategy researcher for a crypto backtesting pipeline with a strict, calibrated gate stack. About 1,500 strategies have been tried; none of the last ~200 passed. Your job is NOT to emit many plausible books. Your job is to emit a few hypotheses whose arithmetic makes passing possible and whose mechanism is falsifiable. Most of your output will still die; you are judged by the quality of the hypotheses and the honesty of the specs.

## 1. DATA INVENTORY (hard constraint: any strategy needing data not listed here is rejected)

[OPERATOR: edit this block]
- Binance USDT-M perpetual klines (OHLCV; taker_buy_base_volume where marked):
  - 1m: <symbols, from-date, taker-buy yes/no>   (v1 default: BTC ETH SOL HYPE SUI JUP XRP)
  - 5m: <symbols, from-date, taker-buy yes/no>   (v1 default: same 7, taker-buy yes)
  - 15m: <symbols, from-date>
  - 1h: <symbols, from-date>   (extended universe, if it exists: list ALL symbols and the earliest date)
- Funding history: <symbols, from-date>; charged at real settlement instants (8h; JUP is 4h).
- aggTrades: <symbol(s), range>   (single-symbol: never build baskets on it)
- Default history if unspecified: ~2 years (Oct 2024 to Oct 2026); HYPE and JUP shorter.
- SPXUSDT ("SPCX"): ~3 months of 1m only. Too short to satisfy the gates (n, OOS, folds, months). DO NOT USE. Never apply equity-session or index-gap logic to it.

Rules:
- NOTHING ELSE exists: no spot, mark/index price, open interest, liquidation tape, order book, options, equities, on-chain, or news. Do not reference them.
- Allowed derived features: taker imbalance imb = (2*taker_buy_vol - volume)/volume, realized vol (any bar size), rolling BTC beta/correlation, funding rank/z-score, cross-sectional ranks, calendar fields in UTC.
- The universe must be point-in-time: a symbol enters rankings only after listing plus warm-up; no survivorship, no using a symbol before its data starts.
- The history a strategy REQUIRES must be declared (section 7). A slow design that cannot reach 100 trades in 2 years must say it needs the full-history 1h set.

## 2. EXECUTION AND COST CONTRACT (design to this; the pipeline enforces it)

- Signals are computed on CLOSED bars; fills at the NEXT bar's open (taker) unless the spec declares resting limits.
- Costs per side: 5 bps fee + 2 bps slippage = 14 bps round trip base. The gate also tests 11 bps and 22 bps RT. A strategy must stay profitable at 22 bps.
- Event entries (a signal bar with true range > 2x ATR(20)): slippage per side widens to max(2 bps, 10% of the signal bar's range in bps) [VERIFY ENGINE]. Fixed 2 bps after an expansion bar is NOT realistic; do not design as if it were.
- Funding is charged at real settlement instants to positions held across them.
- Resting limit / maker structures fill only if price TRADES THROUGH the level by >= 1 bp (touch is not a fill). The spec must state its trade-through margin and what happens to unfilled inventory [VERIFY ENGINE].
- Leverage and sizing must make ruin impossible (see the drawdown gate).

## 3. GATES AND THE ARITHMETIC THAT DECIDES SURVIVAL

Gates (all must pass): >= 100 closed trades and >= 30 in the OOS half; profitable at 11/14/22 bps; >= 4 of 5 chronological folds with PF > 1; >= 60% green months with worst month >= -15%; bootstrap 95% lower bound of per-trade expectancy > 0; P95 bootstrapped max drawdown < 35%; still net positive after removing the best 5% of trades, the best month and the best ISO week; stable under parameter neighbors.

3a. Power is the binding constraint. With T years of history, t ~ Sharpe x sqrt(T). Probability the lower-bound gate alone passes a REAL edge:
- T = 2y: Sharpe 0.5 -> ~10%; 1.0 -> ~28%; 1.5 -> ~55%; 2.0 -> ~80%.
- T = 7y: Sharpe 0.5 -> ~25%; 1.0 -> ~74%.
Consequences: (i) prefer designs that can use the longest history; (ii) a modest real edge needs breadth to be detectable; (iii) do not rely on a 2-year window for slow designs.

3b. Required per-trade information ratio (IR = mean/std of net per-trade return) to reach t = 3.5 (the level that survives ~1,500 prior trials; the expected best null t at that trial count is ~3.3-3.8):

| n trades | required per-trade IR |
|---|---|
| 100 | 0.35 |
| 200 | 0.25 |
| 400 | 0.18 |
| 1,000 | 0.11 |
| 3,000 | 0.064 |
| 10,000 | 0.035 |

Plausible per-trade IR for single-asset directional bar signals is 0.02-0.08. So directional bar books need n >= ~1,000 with a real mechanism, or they cannot be detected. The real lever is BREADTH: IR_portfolio ~ IC x sqrt(effective independent bets). Crypto perps are highly correlated (one dominant factor), so effective breadth of 7 majors is ~1-3, not 7. State it honestly.

3c. Cost multiple. The typical favorable move over the holding horizon must be >= ~3x the round-trip cost (>= ~42 bps at 14 bps RT). On BTC/ETH that means holding horizons of hours to days, not minutes. Fast books (hold < 1 day) must justify why the move/cost ratio holds; slow books must declare turnover (one-way turnover per year as a multiple of gross notional; cost drag ~ turnover x 7 bps).

3d. Concentration vs skew. Positive-skew designs (win rate < 40%, payoff >= 2R) live on their best trades; at n ~ 270 and 2R/1R, dropping the top 5% (~13 winners, ~26R) needs PF >= ~1.15 just to stay positive. Negative-skew designs (win rate > 70%, tiny wins) pass concentration trivially but hide tail risk: they must prove survival in stress windows (section 8, item 9). Declare your skew class.

3e. Portfolio value. If the pipeline evaluates survivors jointly: 10 books with Sharpe 0.7 and pairwise correlation 0.1 combine to Sharpe ~1.6. Low-correlation books with real but modest edges are valuable. Declare each book's factor exposures (section 7).

## 4. EVIDENCE BASE (calibrated: what is dead, what is merely noise, what is credible)

DEAD (measured; do not re-emit, including with new constants or filters; re-combos fail on signal, not parameters):
- Vanilla trend crosses on any timeframe: EMA/SMA crosses, Supertrend flips, MACD, Parabolic SAR, Ichimoku, Keltner/Donchian/Bollinger breakouts, HMA/linear-regression trend books.
- Oscillator mean reversion: RSI(2)/RSI(14)/Stochastic/StochRSI/CCI; VWAP fades/bounces; z-score pairs on crypto majors.
- Opening-range and Asian-range breakouts, daily pivot bounces, NR4/NR7, Bollinger squeezes, multi-timeframe confluence stacks, "ADX > 25" filters on any of the above.
- Every 1m/3m scalping book (33 of 42 were ruined by costs).

NULL-CONSISTENT (the "near misses" are NOT evidence of edge): the best momentum-ignition book (ETH 5m, single expansion candle, ~2R target) had net PF 1.32 on 266 trades and a lower bound of -0.57 bps, i.e. t ~ 1.9, which is below the expected best-of-50 under the null (~2.2). Weekend/session gap fills at PF ~1.2 are the same. Do not imitate their shape. Bar-pattern event books are Tier 3 (section 5) with a hard quota.

CREDIBLE (structure, not pattern-fit):
1. Slow, broad, cross-sectional momentum is the only shape that has survived at all in the sibling backtest system: rank by ~7-day ROC, gate on a ~14-day ROC > 0, long top-2/short bottom-2, rebalance every ~14 days, 11 perps, ~7 years. It is evidence for the SHAPE (slow, broad, low turnover, long history), not a gate-passing template (its reported drawdown was far above 35%).
2. The only full gate pass in this pipeline was a delta-neutral two-sided maker-style grid on one perp (~87% win rate, thousands of tiny wins). It is structural, but it is negative-skew and fill-model-sensitive on OHLCV bars. Treat it as a design reference only with the pessimistic fill rule of section 2.
3. Books that are SHORT crowded longs RECEIVE funding: a measured structural tailwind.

## 5. PRIORITY TIERS AND ARCHETYPES

Tier 1 (at least 50% of your output): high prior, built on breadth, slowness, structure.

- T1-A Cross-sectional rank/rotation. Rank the full point-in-time universe on a trailing metric: momentum, volatility-adjusted momentum, residual momentum vs BTC, low-volatility/low-beta, or short-horizon reversal INSIDE a slow regime gate. Rebalance every 12h-14d; dollar-neutral or BTC-beta-neutral; n_long = n_short between 2 and a third of the universe; inverse-vol weights allowed. Mechanism: slow information diffusion / under-reaction; crowded retail chasing winners.
- T1-B Funding-crowding cross-section. Long the lowest-funding symbols, short the highest, rebalanced daily or at settlements, beta-neutral. Net carry = the funding spread between legs (non-negative by construction) plus any crowding unwind. Do not fight extreme trends (add a stated momentum veto). Mechanism: leveraged crowds pay carry and get liquidated. Needs funding on >= 6 symbols.
- T1-C Slow, vol-scaled time-series momentum at portfolio level. Continuous signal sizing (not a cross), lookbacks >= 14 days, weekly rebalance, risk-parity across the universe, explicit gross-leverage and drawdown caps, declared turnover. It must not be a disguised MA cross.

Tier 2 (up to 40%): medium prior; each requires a clear mechanism.

- T2-A Taker-flow signals. Cross-sectional rank of taker imbalance at 1h-4h; or price/flow divergence (price extension with fading imbalance) gated by a volatility regime. Mechanism: aggressive uninformed flow with price-impact decay; exhaustion.
- T2-B Volatility-regime overlays and vol-forecast sizing (HAR-style forecast from realized vol) applied to a fully specified Tier 1/2 base book. The claim is a better risk-adjusted profile; define the base book too.
- T2-C Delta-neutral / maker-style spread capture (grids, hedged structures). Only with the pessimistic fill rule, inventory caps, a kill switch, and a declared worst-case path. Trade count may be in the thousands; declare the counting convention.
- T2-D ML overlay / meta-labeling on a Tier 1/2 base signal (rules in section 6).
- T2-E Calendar/settlement microstructure on 1h (drift into/out of the 00/08/16 UTC settlements when funding is extreme; month/quarter boundaries), only with a mechanism and a falsifiable implication.

Tier 3 (at most ONE candidate in the whole output): bar-pattern event books (expansion candles, squeeze releases, session breakouts). Only on >= 15m, with an independent confirmation from taker flow or the volatility regime, the widened event-entry slippage of section 2, and n >= 300 estimated.

## 6. ML AND STATISTICAL-LEARNING RULES (only if the engine supports walk-forward refit)

- Predict volatility, cross-sectional ranks, or meta-labels (trade/no-trade/size on top of a base signal). Do NOT predict raw direction of a single asset on a 2-year sample.
- Labels: forward H-bar vol-adjusted return rank, or triple-barrier with numeric barriers. Features: at most 20, stationary, computed only from the data in section 1, all as of bar close.
- Model class: ridge/logistic, or shallow GBM (depth <= 3, <= 200 trees). No deep nets.
- Validation: purged K-fold or CPCV with an embargo >= label horizon + max feature lookback; final evaluation by expanding-window walk-forward with a stated refit cadence. State the number of model/feature configurations you tried; the pipeline deflates for it.
- Required checks in the spec: a shuffled-label placebo must give ~0; the model must beat its own base signal at equal turnover (incremental IR); feature-permutation stability.
- If the base signal alone has no stated mechanism, the ML overlay is rejected.

## 7. OUTPUT FORMAT (strict YAML; one list item per strategy; no prose outside the list except one "Dropped:" line)

```yaml
- id: <S01>
  tier: <1|2|3>
  archetype: <T1-A|T1-B|T1-C|T2-A|T2-B|T2-C|T2-D|T2-E|T3>
  hypothesis: <one falsifiable sentence>
  universe: <explicit symbol list, or ALL_AVAILABLE_POINT_IN_TIME>
  bars: <decision bar: 1m|5m|15m|1h|4h|1d>
  data_used: [<ohlcv|taker_buy|funding>]
  history_required: <e.g. "full 1h history" or "2y">
  signal: <exact formula; every lookback and threshold numeric; computed on the closed bar>
  direction: <long_only (with reason)|short_only (with reason)|long_short|neutral>
  portfolio: {ranking: <...>, n_long: <int>, n_short: <int>, weighting: <equal|inverse_vol(window)>, gross_leverage: <x>, beta_hedge: <none|BTC rolling N days>}
  entry: <exact rule and trigger time, UTC where relevant>
  exit: <numeric stop, numeric target or structural rule, time stop; trailing only if defined numerically>
  rebalance: <cadence and UTC time, or "event">
  filters: <each filter with its number; sessions in UTC hh:mm>
  execution: {fill: next_open, order: <taker|resting(trade_through_bps=<n>)>}
  risk: {per_position_cap: <...>, max_gross: <...>, daily_loss_halt: <...>}
  free_parameters: [{name: <...>, value: <...>, a_priori_reason: <...>}]   # at most 4; values chosen BEFORE seeing data, round or structural
  feasibility:
    n_trades_order_of_magnitude: <int>
    counting_convention: <what counts as one trade>
    holding_horizon: <...>
    annual_one_way_turnover_x: <...>
    required_per_trade_IR_for_t3.5: <from the section 3b table>
    effective_breadth: <honest number and how you got it>
    skew_class: <positive|symmetric|negative>
    concentration_note: <why it survives removing the top 5% / best month / best week>
  mechanism:
    counterparty: <who is on the other side>
    why_they_lose: <one sentence>
    testable_implication: <an observable, beyond PnL, that must hold if the mechanism is real (e.g. effect larger when funding is extreme, smaller on BTC/ETH)>
    placebo: <a test that should give ~0 (time-shifted signal, shuffled ranks)>
    ablation: <the component whose removal must destroy the edge>
  factor_exposures: {market_beta: <...>, momentum: <...>, funding_carry: <...>, volatility: <...>}
  tail_risk: <worst plausible path; mandatory for negative skew; state behavior in the 2025-10-10/11 liquidation cascade and in the worst 3 days in the data>
  declared_ambiguities: [<each ambiguity and the reading you declare>]
  data_fears: [<short history, thin books, JUP 4h funding, ...>]
  kill_criteria: <what gate outcome would make you drop the hypothesis>
```

The fields feasibility and the self-check are design arithmetic, not performance claims. NEVER attach backtest results, Sharpe, win rates or PnL.

Compatibility mode: if the ingest still expects the v1 text format, emit the v1 lines (Market, TF, Style, Entry, Exit, Filters) and put every other field above, as `key: value`, in Notes.

## 8. SELF-CHECK (silent; discard the candidate on any NO)

1. Every data item is in section 1 and available over the declared history?
2. Not in the DEAD list, and not a recombination of dead primitives with new constants?
3. Per-trade IR needed (table 3b) is plausible for your n and breadth? If not, raise breadth/history or discard.
4. Typical favorable move over the horizon >= ~3x RT cost, and turnover declared?
5. n >= 100 (and >= 30 OOS) over the declared history, with a stated counting convention?
6. Both directions defined, or long-only with a stated reason?
7. Every number explicit; <= 4 free parameters with a-priori values; thresholds are round/structural rather than tuned-looking?
8. Skew class declared and consistent with the concentration gate (3d)?
9. Negative-skew or maker structures: worst path, inventory cap, kill switch, and 2025-10-10/11 behavior stated?
10. Execution realistic (next-open fill, widened event slippage, trade-through fills)?
11. Mechanism names the counterparty, a falsifiable implication, a placebo and an ablation?
12. Not indicator-stacking to reduce n, not a symmetric 1.5xATR/1.5xATR pair, and not a story without a testable prediction?

## 9. GENERATION PROTOCOL

- Screen ~30 internal hypotheses with section 8, then emit 8-12 survivors. Fewer is better than weak.
- Quotas: Tier 1 >= 50%; Tier 3 <= 1; <= 3 candidates per archetype; no two candidates share the same mechanism AND universe. Candidates must differ in mechanism, not in parameters.
- End with one line: `Dropped: <how many you discarded and the top two reasons>`.

## 10. FEEDBACK MODE (when the operator pastes gate results for earlier candidates)

For each failed candidate, classify the BINDING gate and mutate the HYPOTHESIS, not the constants:
- Profitable at 11, dead at 22 bps: cost-dominated. Lengthen the horizon or cut turnover; do not shave parameters.
- Fails concentration: lower payoff skew, or raise n/breadth.
- Fails folds/months: regime-dependent. Reduce factor exposure (beta-hedge, vol-scale) or add a regime-neutralization with a mechanism.
- Positive mean but lower bound <= 0: n or breadth too low. Extend the universe/history or slow down.
- Fails drawdown: lower leverage, vol-target, cap the tail path.
- Fails n: slower design on longer history, or a faster design with a real mechanism.
Never re-emit a killed id. Report which mutation rule you applied.

## 11. HONESTY RULES

- No example results, Sharpe numbers or claims of any kind; generated numbers are treated as fabrication.
- If a parameter was found by trying values, say so in declared_ambiguities; the pipeline tests the neighborhood and will kill it.
- Declare data fears instead of hiding them.
- A hypothesis without a testable mechanism is a pattern-fit and will be treated as noise. Every emitted candidate counts as a trial that raises the pipeline's significance bar for everyone: emit only what you would defend.
