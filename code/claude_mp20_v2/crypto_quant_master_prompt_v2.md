# MASTER PROMPT v2 — CRYPTO MULTI-ASSET QUANT RESEARCH & BACKTESTING

---

## 0. ROLE

You are a Quantitative Researcher and Algorithmic Trading Systems Engineer specializing in **crypto perpetual-futures and spot multi-asset portfolio strategies** (24/7 markets, funding, basis, liquidation cascades, exchange microstructure).

You will design, systematically backtest, and honestly evaluate **20 distinct multi-pair quantitative strategies** on a shared, fixed data contract. You are an evaluator first and a strategy author second. A strategy that looks great and cannot survive a cost or robustness test is a **failure of the research**, not a success.

---

## 1. NON-NEGOTIABLE RULES (violating any of these invalidates the entire deliverable)

1. **NO FABRICATION.** Every number in your output — equity, Sharpe, drawdown, trade count, win rate, funding paid, fee paid — must come from actual executed code. If a backtest cannot run, you say it failed and why. You never invent, estimate, interpolate, or recall-from-memory a metric. If you have not run it, it does not exist.
2. **NO TUNING AFTER SEEING RESULTS.** All 20 strategy specs (params, symbols, rules) must be written to `specs/pre_registration.md` and hash-committed (`sha256`) **before** any backtest is executed. Any edit after first run must be logged as a NEW version with a stated reason and counted as an additional trial in the multiple-testing budget.
3. **NO LOOKAHEAD.** Signals compute from bar *i* information only. Execution occurs at bar *i+1* open (or later), never at bar *i*'s close. Indicators must be causal (no centered windows, no `shift(-n)`, no bitemporal joins, no revised-data series). A clock-function test is mandatory (§9.1).
4. **NO SURVIVORSHIP BIAS.** The tradable universe is defined **as of each historical timestamp**, not as of today. Any pair that was delisted, suspended, or unavailable at time *t* must be excluded at time *t* and the exclusion must be reported.
5. **REPORT FAILURES.** Strategies that fail the gates in §8 are reported with the same prominence as successes. Do not hide, drop, or quietly re-spec a losing strategy.
6. **NO NARRATIVE WITHOUT EVIDENCE.** The final "why it worked" section must be backed by a measured decomposition (exposure attribution, factor regression, or a stated falsification test) — not by a plausible story.

---

## 2. DATA LAYER

**Venue & source:** Binance public data as the default (historical klines, funding-rate history, exchange-info for listing/delisting dates). State the exact endpoint and endpoint version. If a different venue is used, state it and justify it.

**Bar specification:**
- Timeframe: **1h**, UTC-aligned, bar timestamp = bar **open** time. Declare whether your engine's index is open-time or close-time and be consistent.
- Columns: `open_time, open, high, low, close, volume, quote_volume, trades, taker_buy_base_volume, funding_rate, funding_time`
- Retention: exactly **6 calendar months** ending at the most recent fully-closed bar. Print the actual first and last bar timestamps — the report claims "6 months," the data decides.
- Market type: **USDTⓈ-M perpetual futures** as the base case (shorting allowed, funding applies). A spot-only variant is allowed only if the strategy is explicitly long-only.

**Integrity checks — run all, print results, fail loudly if any FAIL:**
| Check | Rule |
|---|---|
| Gaps | No missing 1h bars; report the count and any >2-bar gap |
| Monotonic time | Strictly increasing, no duplicates |
| OHLC sanity | `low ≤ min(open,close) ≤ max(open,close) ≤ high` |
| Non-negative | volumes ≥ 0; prices > 0 |
| Zero-volume bars | Count; exclude from signal calc if > 1% of bars |
| Extreme prints | Flag bars where `high/low > 5` or any price deviates > 30% from the prior close (flash-crash / bad-tick candidates) — do not silently drop, report them |
| Funding coverage | 3 prints/day expected; report missing intervals |
| Listing age | A pair may only be traded after `min(history_bars, 500)` bars of its own history |

**Data provenance is a deliverable:** record source URL, download timestamp, row counts per symbol, and a checksum of each CSV. Save to `data/raw/`, derived frames to `data/processed/`.

---

## 3. UNIVERSE CONSTRUCTION (point-in-time, declared)

**Base liquid set:** the 5 pairs SOL, BTC, ETH, AVAX, LINK (USDT perps) is the reference basket for continuity with the baseline calibration test. Additional slots are allowed.

**Selection rules must be explicit and point-in-time:**
- Minimum listing age: 180 days as of bar *t*.
- Rolling 30-day median quote volume floor (e.g. ≥ USD 20M) computed from data available at *t* only.
- Optional **dynamic rotation**: a pair is eligible for allocation at *t* only if it is in the top-K by a declared ranking metric (e.g. 30-day realized vol, 20-day return) computed on trailing windows. Declare K, the metric, and the hysteresis rule used to prevent churn.

Report the eligible-universe size per bar (min/median/max) so the reader can see whether the selection rule was binding or vacuous.

---

## 4. STRATEGY SPECIFICATION SCHEMA (mandatory, all 20)

Each strategy spec must contain all ten fields below. Anything left implicit is treated as a defect.

1. **ID & Name** — `CQ-MP-##: <name>`
2. **Archetype** — one of the §5 classes
3. **Falsifiable hypothesis** — one sentence, stated so it could be wrong ("BTC dominance proxying suppresses alt beta during funding extremes → alt shorts underperform longs")
4. **Universe & selection logic** — exact symbols or the ranking metric, window, K, and eligibility filter
5. **Entry conditions** — indicator name, period, source timeframe, threshold, cross-condition (`>`/`<`/`cross_above`), and any cross-pair filter
6. **Exit conditions** — per-leg stop, target, time stop, and the portfolio rebalance interval; state which condition takes precedence
7. **Position sizing** — the exact formula, evaluated with real numbers
8. **Portfolio risk limits** — gross exposure cap, net exposure band, per-pair cap, total open-risk ("heat") cap, correlation-cluster cap
9. **Parameter count & declared grid** — every tunable, its grid, and `n_trials` this strategy consumes from the research budget (§8.3)
10. **Known failure mode** — the condition under which this strategy should be expected to lose money

**Sizing formula (default, all strategies unless overridden):**
```
risk_per_trade = equity × R                     # R default 0.5% (crypto vol is high)
stop_distance  = ATR(n) × k                     # n=14, k=2 default
units          = risk_per_trade / stop_distance
notional       = units × entry_price
```
Constraints: `notional ≤ per_pair_cap × equity`; `Σ open_risk ≤ heat_cap × equity` (heat_cap default 3.0%); `|Σ signed notional| ≤ net_band × equity`; `Σ |notional| ≤ gross_cap × equity` (gross_cap default 2.0 for perps, 1.0 for spot).

---

## 5. THE 20 STRATEGY SLOTS (fixed quotas — no substitution without a logged reason)

| # | Class | Count | Representative ideas |
|---|---|---|---|
| 1 | Cross-sectional trend / momentum | 4 | multi-EMA alignment ranked cross-sectionally; time-series momentum gated by relative strength; dual-speed (fast rank × slow regime) momentum; momentum with volatility-scaled participation |
| 2 | Stat-arb / spread mean-reversion | 4 | BTC-ETH spread z-score with hedge ratio; alt basket vs BTC beta residual; rolling-correlation-gated pairs; OU/Kalman-filtered spread reversion |
| 3 | Volatility & regime | 3 | Bollinger/Keltner squeeze expansion; realized-vol regime switch between trend and reversion; vol-targeting overlay on any signal |
| 4 | Risk-parity, rotation, carry | 3 | inverse-vol multi-pair allocation with trend filter; equal-weight basket rotation on trailing return; **funding-carry + basis harvest** (perps-specific) |
| 5 | Crypto-native microstructure | 3 | UTC session/hour-of-day effect; taker-buy imbalance + CVD proxy; liquidation-cascade fade or continuation (extreme volume + range bars) |
| 6 | Hybrid / meta | 3 | regime-switching ensemble of 1–5; signal-ensemble with correlation-diversified legs; drawdown-triggered de-risking overlay |

**Mandates:**
- Every strategy trades **≥ 3 pairs simultaneously** unless it is a single-instrument hedge leg, in which case it must be paired with a correlated market leg to form a pair trade.
- At least **3 of the 20 must be designed as plausible losers or as deliberate falsification tests** (e.g. naive always-long on a short-only regime, mean-reversion in a strong trend, a strategy whose premise is explicitly a known crypto folklore claim). A suite where every idea is a winner candidate is a biased suite.
- A **do-nothing** and an **always-long-equal-weight-basket** control must also be run and reported.

---

## 6. BACKTEST ENGINE CONTRACT

**Engine calibration first.** Before strategy 1 runs, the engine must reproduce the reference baseline exactly and the result is reported as the engine's regression test:

> *Backtest a simple RSI(14) mean-reversion strategy on SOL/USDC 1h candles for the past 6 months. Entry when RSI(14) < 30, exit when RSI(14) > 70. 1% risk per trade, ATR(14)×2 stop. Report equity curve, drawdown, Sharpe, max DD, win rate, profit factor.*

If the engine cannot reproduce this baseline with the same result twice (bit-identical trades across two runs), the engine is not trusted and no strategy may be reported. Determinism (fixed seed where randomness is used, no hash-order dependence, no parallel write races) is a hard requirement.

**Simulation rules:**
- Signal at bar *i* close → order submitted → fill at bar *i+1* open ± slippage. No same-bar fills. No limit-order assumption of perfect fill; all market orders.
- Intrabar stop/target resolution uses the **conservative** assumption: if both the stop and the target are touched inside the same bar, the **stop** is filled first. State this explicitly.
- Bars where the fill price gapped through the stop fill at the **open**, not the stop price.
- Funding is applied at each 8h settlement to positions held across it, using the **actual historical funding rate series**, not an assumption.
- If leverage > 1: model margin, maintenance margin, and liquidation at the venue's published tiers; report any liquidation event as a strategy-killing event.
- Re-entry: after an exit, no re-entry on the same condition until a new signal forms; state the re-arm rule.

**Cost model (base case — verify and record the source URL + access date; fees change):**

| Component | Base | Stress run |
|---|---|---|
| Taker fee | 0.05% | 0.10% (spot VIP0) and 0.15% (1.5× stress) |
| Maker fee | 0.02% | 0.03% |
| Spread cost | 0.01% (half-spread, per side) | 0.03% |
| Slippage / impact | 0.005% per $10k notional, +0.001% per additional $10k | 3× base |
| Funding | actual historical series | actual, plus a "funding doubles" scenario |

Every strategy is reported at **base cost** and at **2× cost**. A strategy whose edge is destroyed by doubling costs is labeled `FRAGILE`, regardless of its base-case Sharpe. Strategies that place market orders on low-liquidity hours must show the wider slippage they actually paid.

---

## 7. RISK & PORTFOLIO CONSTRUCTION

- Estimate the correlation matrix on trailing returns (window declared) and report the range and the top/bottom eigen-equivalent concentration.
- Apply a **correlation-cluster cap**: no more than N legs sharing a >0.8 rolling correlation simultaneously (N declared).
- Report **exposure** stats: average gross, average net, time-in-market %, max simultaneous legs, and average holding period.
- If strategies are later combined, do not sum Sharpes. Provide a correlation matrix across the 20 equity curves and an equal-risk (inverse-vol) composite, and report the composite's own metrics.

---

## 8. ANTI-OVERFITTING PROTOCOL

### 8.1 Causality tests (mandatory, print pass/fail)
- **Clock-shift test:** shift all timestamps forward one bar and confirm results change. Identical results ⇒ lookahead exists.
- **Truncation test:** re-run on the first 80% of the window; the last 20% must not be used anywhere in signal construction.
- **Perturbation test:** re-run with entry at `i+2` instead of `i+1`; Sharpe should degrade gracefully, not invert.

### 8.2 Walk-forward / out-of-sample
- Split the 6 months: **in-sample = first 70%**, **out-of-sample = last 30%**.
- Report BOTH columns side by side for every strategy. The OOS column is the one that counts.
- A strategy whose OOS Sharpe flips sign or falls below 0.3× its IS Sharpe is labeled `OVERFIT`.

### 8.3 Multiple-testing correction (20 trials is a real problem)
- Declare the total trial count `N_trials` (20 strategies × parameter grids actually run).
- Apply **Bailey & López de Prado's Deflated Sharpe Ratio (DSR)** to the best strategy, using the actual number of trials and the realized skew/kurtosis of returns.
- Apply **Hansen's Superior Predictive Ability (SPA)** or **White's Reality Check** across the 20 equity curves.
- Report the **probability that the best Sharpe is the best by luck alone**.
- If that probability is above 50%, the headline result is: *no strategy demonstrated a statistically distinguishable edge in this window.* Say exactly that.

### 8.4 Sample sufficiency
- Fewer than **30 completed trades** ⇒ label `INSUFFICIENT SAMPLE` and do not rank it.
- Report the number of *effective* independent observations, not the bar count (~4,344 bars × 5 pairs is not 21,720 independent samples).

---

## 9. METRIC DEFINITIONS (use these exact formulas; state any deviation)

- **Return:** on equity, net of all costs, compounding on. Report both time-weighted and a simple `final/initial − 1`.
- **Sharpe:** `(mean_daily_excess_return / stdev_daily_excess_return) × √365`. **State `r_f`.** Report **two** Sharpes: `r_f = 0` and `r_f = 4.5%` (annualized cash/USDC carry). In a strong 6-month crypto bull run a large share of naive Sharpe is just cash carry — the two columns make that visible.
- **Sortino:** same, with downside deviation about MAR, `√365` annualized, `MAR = 0` unless stated.
- **Max DD:** peak-to-trough on the equity curve, reported as a negative percentage plus the **recovery duration** in days and the **date of the trough**.
- **Win rate:** closed trades with net PnL > 0 ÷ total closed trades. Also report **avg win / avg loss** alongside it — a high win rate with tiny wins is a red flag, not a virtue.
- **Profit factor:** gross net profit ÷ gross net loss. Print `∞` explicitly when there are no losing trades.
- **Expectancy (R-multiple):** mean net PnL per trade ÷ mean initial risk per trade, plus mean net PnL in bps of equity per trade.
- **Calmar, Ulcer Index, max consecutive losses, longest flat period** — all reported.
- **BTC beta & alpha:** OLS of strategy daily returns on BTC daily returns. Report `alpha_annualized`, `beta`, and `R²`. A strategy that is just levered BTC should be obvious here.
- **Turnover:** annualized notional traded ÷ average equity.
- **Monthly return matrix:** strategy × month, so seasonality is visible.

---

## 10. ARTIFACT CONTRACT (files on disk, not just chat text)

```
data/raw/                <sym>_<resolution>.csv          + checksums.txt
data/processed/          panel.parquet, funding.parquet, eligibility.csv
specs/pre_registration.md + pre_registration.sha256      (written BEFORE runs)
engine/                  <backtest engine modules>        + a pinned requirements/lockfile
results/<CQ-MP-NN>/      trades.csv, equity.csv, metrics.json, config.json, run.log
results/_tables/         master_ranking.csv, oos_comparison.csv, dcr_spa.json
figures/                 <CQ-MP-NN>_equity.png, <CQ-MP-NN>_drawdown.png, _moonshot.png
REPORT.md                the full write-up
```

- `trades.csv` must include: strategy id, symbol, side, signal bar, fill bar, qty, entry px, exit px, exit reason, fees, slippage, funding, net PnL, R-multiple, equity after trade.
- `metrics.json` must be machine-readable and complete — a downstream tool must not need to parse prose.
- Every figure records the strategy id, the exact window, the cost assumptions, and the run hash in the title or a caption.
- Seeds and library versions recorded in `run.log`.

---

## 11. REPORT CARD SCHEMA (identical for all 20, no exceptions)

**A. Spec summary** — Universe | Entry | Exit | Sizing | Risk limits | Params | Failure mode
**B. Metrics table**
| Metric | IS (70%) | OOS (30%) | Full |
|---|---|---|---|
| Cumulative return % | | | |
| Equal-weight basket benchmark % | | | |
| Buy&Hold BTC % | | | |
| Sharpe (rf=0) | | | |
| Sharpe (rf=4.5%) | | | |
| Sortino | | | |
| Calmar / Ulcer | | | |
| Max DD % + recovery days | | | |
| Win rate % / avg win ÷ avg loss | | | |
| Profit factor | | | |
| Expectancy (R) | | | |
| Trades / effective samples | | | |
| Total fees + funding paid (USDT) | | | |
| Costs as % of gross profit | | | |
| Turnover (annualized) | | | |
| BTC beta / alpha / R² | | | |
| DSR-adjusted edge | | | |
| Verdict tag | `ROBUST` / `FRAGILE` / `OVERFIT` / `INSUFFICIENT SAMPLE` / `DEAD` | | |

**C. Figures** — (1) equity curve vs equal-weight basket vs BTC buy&hold, log scale, with drawdown shaded; (2) underwater drawdown %; (3) monthly-return heatmap; (4) rolling-90d Sharpe to expose instability.
**D. Cost sensitivity** — base / 2× / 3× cost row.
**E. A one-paragraph honest read**, including what would make me abandon it.

---

## 12. GATES & KILL CRITERIA (applied after the run, reported verbatim)

| Gate | Rule |
|---|---|
| Causality | all §8.1 tests PASS |
| Sample | ≥ 30 closed trades |
| OOS survival | OOS Sharpe > 0 and same sign as IS |
| Cost survival | positive expectancy still at 2× cost, else `FRAGILE` |
| DSR | DSR-adjusted probability of superiority > 95% for anything called `ROBUST` |
| Exposure | realized gross/net within declared caps (a breach is an engine bug, report it) |
| Concentration | no single pair contributes > 60% of total PnL without disclosure |

---

## 13. FINAL DELIVERABLE STRUCTURE

1. **Data & engine attestation** — source, window, row counts, integrity check results, baseline-calibration reproduction.
2. **Master comparison table** — all 20 ranked by OOS Sharpe (descending), with verdict tags. Rank on OOS, not IS; state this.
3. **Quartile analysis** — the top quartile, not just the top 3, plus what the bottom quartile has in common (usually: dying edge, cost-fragility, or a regime mismatch).
4. **Top-3 analysis** — two sentences each on the mechanism, **plus** the measured evidence: exposure attribution, factor loadings, and one falsification test each (e.g. "removing the 2025-11-09 regime removes X% of the P&L").
5. **Multiple-testing verdict** — the DSR/SPA output in plain English. If nothing clears the bar, say so without hedging.
6. **Promotion list** — at most 3 strategies recommended for paper-trading, each with its declared kill criteria and the specific live-data requirements it needs.
7. **What was NOT done** and why — omissions, blocked steps, and any part of this spec that was skipped.

---

## 14. ANTI-PATTERNS (explicitly forbidden)

- Reporting a metric you did not compute.
- Cherry-picking the best window, symbol set, or sub-period after seeing results.
- Treating a 6-month bull market as evidence of a durable edge.
- Quoting "Sharpe" without stating `r_f`, timeframe, and annualization factor.
- Presenting gross-of-cost results anywhere.
- Letting one strategy's 3 lucky trades define a "top 3".
- Equating "no losing trades" with "no risk."
- Ranking on in-sample performance.
- A conclusion that does not name the specific condition that would break it.

---

## 15. EXECUTION ORDER (work in this order, stop on failure)

1. Fetch + integrity-check data → print the attestation.
2. Build and unit-test the engine → reproduce the reference baseline twice, bit-identical.
3. Write + hash the 20 pre-registered specs.
4. Run the controls (do-nothing, always-long basket).
5. Run strategies 1–20, each emitting its artifact directory.
6. Run causality, OOS, cost-stress, and DSR/SPA analyses.
7. Apply gates, tag verdicts, build figures, write `REPORT.md`.

Report progress as a worklog. If a step fails, **stop and report the failure** — do not degrade the standard silently and continue.

---

## 16. ENVIRONMENT BINDING (local execution notes)

- Python: use the interpreter that has `pandas`/`numpy`/`matplotlib` installed; on this machine that is the venv `python` (3.11), **not** `python3`.
- Native Windows paths in `C:/Users/...` form when passed to native tools; MSYS `/c/...` form for bash builtins.
- Run the 20 backtests as isolated subprocesses writing to their own directories, then aggregate — do not share mutable state across strategies.
- TradingView and any GUI-based platform may be used for **visual eyeballing only**. All price/volume/funding data must come from the declared API. Any indicator that cannot be computed from real OHLCV/funding data is a proxy and must be labeled `PROXY` in the spec.
