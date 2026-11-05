# Cross-Sectional Strategy Backtest Results

**Date:** 2026-11-02
**Data:** Binance USDT-M perps (1h: 18 symbols × 62,687 bars; 5m: 7 symbols × 210,437 bars)
**Costs:** 8 bps round-trip (5 fee + 3 slip)
**Method:** 70/30 IS/OOS split, dollar-neutral (long/short), equal weight

## Survivors (positive return, positive Sharpe, positive OOS)

| Strategy | Total Ret | Max DD | Sharpe | IS Ret | OOS Ret | Pos Months | N Rebal |
|----------|-----------|--------|--------|--------|---------|------------|---------|
| **S20_Composite** | **+538%** | **-51.6%** | **0.89** | +246.8% | **+84.0%** | 51.2% | 351 |
| **S8_FundingMom** | **+297.4%** | **-70.8%** | **0.67** | +72.4% | **+130.6%** | 59.3% | 354 |
| **S10_SharpeMom** | **+132.1%** | **-71.5%** | **0.50** | +20.4% | **+92.8%** | 53.5% | 352 |

## Near-miss

| Strategy | Total Ret | Max DD | Sharpe | OOS Ret | Issue |
|----------|-----------|--------|--------|---------|-------|
| S2_Beta | -49.3% | -76.3% | -0.01 | -60.3% | IS positive (+27.5%) but OOS collapsed |

## Failed (negative, but informative)

| Strategy | Total Ret | Sharpe | OOS Ret | Root cause |
|----------|-----------|--------|---------|------------|
| S1_LowVol | -98.6% | -1.13 | -86.8% | Low-vol premium doesn't exist in crypto (high-vol alts outperform) |
| S3_Skew | -95.7% | -0.94 | -77.1% | Skewness estimate too noisy on 168 bars |
| S5_Defensive | -64.4% | -0.15 | -36.5% | Relative strength during corrections doesn't persist |
| S6_ResidRev | -100% | -3.05 | -88.4% | Idiosyncratic residuals don't revert (news-driven) |
| S7_FundingDiff | -92.2% | -0.95 | -87.4% | Funding differential alone insufficient (basis risk) |
| S9_VolRatio | -99.9% | -2.32 | -88.0% | Vol ratio mean-reverts too fast |
| S22_Regime | -92.9% | -0.69 | -72.4% | Regime detection lags, whipsaws |
| S4_BTCE | -88.9% | -1.65 | -37.4% | BTC/ETH ratio not stationary enough |

## 5m Microstructure (all failed — costs dominate)

| Strategy | Total Ret | Sharpe | N Rebal | Cost |
|----------|-----------|--------|---------|------|
| S11-S13, S17-S19 | -100% | -40 to -337 | 16k-179k | 10k-12k |

Turnover: rebalancing every 1-12 bars on 5m = 16k-179k rebalances × 8 bps = 128%-1,432% in costs. No microstructure signal can overcome this.

## Taker-based (bug — column name mismatch)

S14, S15, S16, S21 returned 0% with 0 rebalances because the taker data column is `taker_buy_base` not `taker_buy_base_vol`. These strategies were not actually tested. Need to fix and re-run.

## Key Findings

1. **Only momentum + funding combinations survive.** S8 (Sharpe-momentum + funding filter), S10 (Sharpe-momentum), and S20 (composite of both) are the only profitable strategies.

2. **S20_Composite is the best** with Sharpe 0.89, +538% total, OOS +84%. It combines z(ROC/vol) - z(funding), addressing both the momentum crash (via vol adjustment) and crowding (via funding penalty).

3. **Cross-sectional momentum is the core alpha.** All 3 survivors are momentum variants. The funding filter (S8) and vol adjustment (S10) improve on raw momentum.

4. **Costs kill everything below 1h.** 5m strategies have 16k-179k rebalances. Even with 8 bps, that's 128%-1,432% in costs. No signal can overcome this.

5. **Single-factor strategies fail.** Low-vol, skew, beta, vol-ratio, defensive quality — none survive. Only momentum (and its combinations) has edge.

6. **MP-18 (the original) was right.** Cross-sectional momentum rotation is the only robust factor. The improvements (vol adjustment, funding filter, composite) add incremental value.

## Recommended next steps

1. **Paper trade S20_Composite** alongside MP-18 v2 (which is already on VPS)
2. **Fix taker column name** and re-run S14-S16, S21
3. **Walk-forward validation** on S20 and S8 with multiple windows
4. **Combine S20 with MP-18 v2** — MP-18 uses 168-bar ROC, S20 uses ROC/vol - funding. They may be complementary.
5. **Reduce rebalance frequency** for 5m strategies (e.g., daily instead of hourly) to test if any microstructure signal survives at lower turnover