# ML4T "Crypto Perpetuals Funding" — backtest verdict

**What was tested.** The funding-rate mean-reversion core of the ML4T case study
(case_studies/crypto_perps_funding): at every eight-hour Binance funding
settlement (00:00 / 08:00 / 16:00 UTC), rank the nineteen perpetual contracts by
their funding rate, go long the five cheapest-to-hold and short the five most
expensive, equal weight within each side, rebalance at the settlement price, and
charge the funding actually paid plus transaction cost. This is the mechanism
replica, not the case study's eighteen-notebook machine-learning pipeline (44
features, GBM/LSTM/TCN), which is not reproduced.

**Universe and data.** All nineteen contracts the case study declares
(AAVE, ADA, APT, ATOM, AVAX, BNB, BTC, COMP, DOGE, DOT, ETH, INJ, LINK, MKR,
NEAR, SOL, SUI, UNI, XRP, all versus USDT). Eleven already lived in the store;
the other eight were downloaded from Binance public REST on 2026-11-22 so the
test covers the full declared universe rather than a lucky subset. Funding
stamps are floored to the second before alignment because part of the history is
stamped at millisecond offsets; a position held over a holding window is charged
every settlement inside that window, not just one.

**Cost schedules (two, because the case study names both).**
- cs_engine: five basis points per leg everywhere (four commission + one
  slippage, the engine's production schedule).
- cs_tiered: majors two basis points, alts four (BTC, ETH, BNB, SOL, XRP are
  the majors; every other name is an alt).

A zero-cost path is computed inside every artifact, so the cost drag is
measured, never derived.

**Primary cell (frozen before the first run):** funding level, five names a
side, cs_engine cost. Its verdict is the verdict.

| window | net return | net Sharpe | max drawdown | zero-cost Sharpe | cost share of capital | run_id |
|---|---|---|---|---|---|---|
| validation, 2022-2023 | +17.00% | +0.39 | −37.58% | +2.32 | 197.17% | bca91748433d0ad9 |
| holdout, 2024-2025 | −59.87% | −1.15 | −62.14% | +1.52 | 119.75% | b90f59d052a85790 |
| beyond history, 2026 | −29.44% | −1.14 | −41.84% | +2.14 | 80.42% | 1a50574b1a5469d3 |

Cost share is the cumulative cost charged as a percentage of starting capital
over the window. Trading happened at one thousand eight hundred forty-three
turnovers per year in the holdout window; the book rebalances every eight hours,
so turnover runs about eighteen hundred forty-three percent of capital per
year, and at five basis points per leg that compounds into more than the whole
starting stake across two years.

**Decomposition of the holdout cell** (run_id b90f59d052a85790): the price leg
contributed +43.56% and the funding leg +16.33% — both positive, so the
underlying mechanism pays — while costs took −119.75%, leaving −59.87%. The
rank correlation between the funding score and the next period's return is
+0.0184, weakly positive: the signal has direction, costs have magnitude.

**Robustness: no parameter choice rescues the holdout.** Every variant is
negative out of sample:
- three names a side, level, cs_engine, holdout: −85.41% return, −1.84 Sharpe
  (run_id 97faaf62f2d475ae)
- funding fourteen-day z-score, five a side, cs_engine, holdout: −85.03%
  return, −2.53 Sharpe (run_id edd75e390e92c710)
- five a side, level, tiered cost (majors two, alts four), holdout: −29.53%
  return, −0.34 Sharpe (run_id d21e5693eac401b5)

Only the tiered-cost holdout cell comes closer to zero, and it is still
negative. In the validation window the same variants can look positive (up to
+109.55% return, +0.97 Sharpe for three names a side), but none of them survives
the holdout. Twenty-four cells on one data set is a multiple-testing family;
none of the twenty-three non-primary cells may rescue the primary.

**Accounting.** Every artifact re-verifies bit-for-bit, and each one closes its
own ledger: ending equity equals starting equity plus price profit-and-loss plus
funding cash flow minus cost, with a residual below one part in a million of
starting capital. The book traded at every eligible stamp in all three windows
(one hundred percent traded share), so nothing was silently skipped.

**Verdict: mechanism without edge.** The funding-rate mechanism genuinely pays
at the gross level — price and funding contributions are positive in validation,
holdout, and beyond-history alike — but transaction cost at eight-hour
rebalancing consumes the entire edge and then some. Net Sharpe is negative in
the holdout (−1.15, run_id b90f59d052a85790) and in the beyond-history window
(−1.14, run_id 1a50574b1a5469d3), while the same book carries a positive
zero-cost Sharpe (+1.52 holdout). This independently confirms the case study's
own published conclusion: the pattern exists, it reverses in the bull run, and
an eight-hourly rebalanced book cannot keep what it earns. The strategy is not
tradable at the declared cost.

**Gates.** Declared before the run: G1 validation Sharpe above zero point five
(fails: zero point three nine); G2 holdout Sharpe above zero (fails: minus one
point one five); G3 holdout return above zero (fails: minus fifty-nine point
eight seven percent); G4 costs must bind (passes); G5 funding contribution
positive (passes: plus sixteen point three three percent); G6 traded at ninety-
five percent of stamps (passes: one hundred percent); G7 ledger identity inside
each artifact (passes: residual below one part per million). Net result fails
G1, G2 and G3, which maps to "mechanism without edge," not a pass.

**Bottom line in plain words.** Buying the perps whose holders pay the least to
keep them long, and shorting the ones whose holders pay the most, does capture
something real at eight-hour funding settlements. But you rebalance every eight
hours across nineteen contracts, and at the exchange's going fees that turnover
costs more than the signal is worth. The book ends the two-year holdout with
about sixty percent less than it started. Do not trade this at the declared
cost.
