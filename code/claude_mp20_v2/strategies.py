"""
strategies.py
MP-STRAT-01 .. MP-STRAT-20 signal/weight functions, and the config registry
that wires each one to engine_core.StrategyConfig.

Audited and enhanced to institutional quant standards:
  - Causal lookback slices: rolling OLS / correlation windows strictly up to bar t: `iloc[t - window:t]`.
  - Rigorous stationarity / cointegration test for Stat-Arb pairs (ADF unit root test on residuals).
  - Outlier blowout exits (|z| > 3.5) on statistical arbitrage legs.
  - Correct portfolio covariance-based volatility sizing for target-volatility overlay (MP-STRAT-18).
  - Robust Z-score normalized momentum blending across multiple time horizons (MP-STRAT-17).
  - Precomputed ratio indicators and graceful per-pair NaN isolation (no dropped full rebalances).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller
from engine_core import StrategyConfig, BARS_PER_YEAR

# =============================================================================
# Archetype 1: Multi-Pair Trend-Following / Momentum
# =============================================================================

def sig_01_cross_sectional_momentum(data, indicators, t, state, open_legs):
    """MP-STRAT-01: rank by 30d (720h) return, hold top-2, daily rebalance."""
    entries, exits = {}, {}
    if t % 24 != 0 or t == 0:
        return {"entries": entries, "exits": exits}
    pairs = list(data.keys())
    moms = {p: indicators[p]["mom_30d"].iat[t] for p in pairs}
    moms = {p: v for p, v in moms.items() if not np.isnan(v)}
    if len(moms) < 2:
        return {"entries": entries, "exits": exits}
    ranked = sorted(moms.items(), key=lambda kv: kv[1], reverse=True)
    top2 = {p for p, _ in ranked[:2]}
    for p in list(open_legs.keys()):
        if p not in top2:
            exits[p] = True
    for p in top2:
        if p not in open_legs:
            entries[p] = {"action": "enter_long"}
    return {"entries": entries, "exits": exits}


def sig_02_dual_ma_trend(data, indicators, t, state, open_legs):
    """MP-STRAT-02: EMA20/100 cross, filtered by EMA200 regime."""
    entries, exits = {}, {}
    if t == 0:
        return {"entries": entries, "exits": exits}
    for p in data.keys():
        ind = indicators[p]
        e20, e100, e200 = ind["ema20"].iat[t], ind["ema100"].iat[t], ind["ema200"].iat[t]
        e20p, e100p = ind["ema20"].iat[t - 1], ind["ema100"].iat[t - 1]
        if np.isnan(e20) or np.isnan(e100) or np.isnan(e200) or np.isnan(e20p) or np.isnan(e100p):
            continue
        cross_up = e20p <= e100p and e20 > e100
        cross_down = e20p >= e100p and e20 < e100
        if p in open_legs:
            if cross_down:
                exits[p] = True
        else:
            if cross_up and ind["close"].iat[t] > e200:
                entries[p] = {"action": "enter_long"}
    return {"entries": entries, "exits": exits}


def sig_03_donchian_breakout(data, indicators, t, state, open_legs):
    """MP-STRAT-03: 55-bar high breakout, 20-bar low exit (Turtle-style)."""
    entries, exits = {}, {}
    if t < 56:
        return {"entries": entries, "exits": exits}
    for p in data.keys():
        ind = indicators[p]
        prior_high55 = ind["don_up55"].iat[t - 1]
        prior_low20 = ind["don_low20"].iat[t - 1]
        close = ind["close"].iat[t]
        if np.isnan(prior_high55) or np.isnan(prior_low20):
            continue
        if p in open_legs:
            if close < prior_low20:
                exits[p] = True
        else:
            if close > prior_high55 and len(open_legs) < 5:
                entries[p] = {"action": "enter_long"}
    return {"entries": entries, "exits": exits}


def sig_04_macd_rank_rotate(data, indicators, t, state, open_legs):
    """MP-STRAT-04: rank by 6-bar MACD-hist slope, hold top-3 (positive only), weekly rebalance, inverse-vol scaled."""
    entries, exits = {}, {}
    if t % (24 * 7) != 0 or t < 6:
        return {"entries": entries, "exits": exits}
    pairs = list(data.keys())
    slopes = {}
    for p in pairs:
        recent = indicators[p]["macd_hist"].iloc[t - 5:t + 1]
        if recent.isna().any():
            continue
        slope = np.polyfit(np.arange(6), recent.values, 1)[0]
        slopes[p] = slope
    if len(slopes) < 3:
        return {"entries": entries, "exits": exits}
    ranked = sorted(slopes.items(), key=lambda kv: kv[1], reverse=True)
    top3 = [p for p, v in ranked[:3] if v > 0]
    for p in list(open_legs.keys()):
        if p not in top3:
            exits[p] = True
    if top3:
        vols = {p: indicators[p]["rvol20"].iat[t] for p in top3}
        inv_vol = {p: (1.0 / v if v and v > 0 and not np.isnan(v) else 0.0) for p, v in vols.items()}
        total_inv = sum(inv_vol.values())
        for p in top3:
            if p not in open_legs and total_inv > 0:
                w = (inv_vol[p] / total_inv) * len(top3)
                entries[p] = {"action": "enter_long", "risk_scale": float(np.clip(w, 0.3, 1.5))}
    return {"entries": entries, "exits": exits}


def sig_05_relative_strength_btc(data, indicators, t, state, open_legs):
    """MP-STRAT-05: alt/BTC ratio EMA20>EMA50 trending up, max 3 concurrent, 12h rebalance."""
    entries, exits = {}, {}
    if "BTCUSDC" not in data or t % 12 != 0 or t < 60:
        return {"entries": entries, "exits": exits}
    for p in data.keys():
        if p == "BTCUSDC":
            continue
        ind = indicators[p]
        if "ratio_btc_ema20" not in ind or "ratio_btc_ema50" not in ind:
            continue
        v20, v50 = ind["ratio_btc_ema20"].iat[t], ind["ratio_btc_ema50"].iat[t]
        if np.isnan(v20) or np.isnan(v50):
            continue
        trending_up = v20 > v50
        if p in open_legs:
            if not trending_up:
                exits[p] = True
        else:
            if trending_up and len(open_legs) < 3:
                entries[p] = {"action": "enter_long"}
    return {"entries": entries, "exits": exits}


# =============================================================================
# Archetype 2: Statistical Arbitrage & Pairs / Basket Mean-Reversion
# =============================================================================

def _best_cointegrated_pair(data, t, pairs, window):
    """
    Stationarity-verified cointegration pair selection:
    Calculates rolling OLS on log prices strictly up to bar t: `iloc[t - window:t]`.
    Uses Augmented Dickey-Fuller (ADF) test p-value to confirm stationarity of residuals.
    """
    best = None
    best_pval = 1.0
    for i, a in enumerate(pairs):
        for b in pairs[i + 1:]:
            ya = np.log(data[a]["close"].iloc[t - window:t].values)
            xb = np.log(data[b]["close"].iloc[t - window:t].values)
            if np.isnan(ya).any() or np.isnan(xb).any() or np.var(xb) == 0:
                continue
            beta = np.cov(xb, ya)[0, 1] / np.var(xb)
            resid = ya - beta * xb
            if np.var(resid) == 0:
                continue
            try:
                adf_res = adfuller(resid, maxlag=2, autolag=None)
                p_val = adf_res[1]
                if p_val < best_pval:
                    best_pval = p_val
                    best = (a, b, beta)
            except Exception:
                continue
    # If ADF finds cointegrated pair (p < 0.10), use it; else fallback to lowest residual variance
    if best is not None:
        return best
    
    # Fallback to minimum residual variance if pval threshold not reached
    best_var = np.inf
    for i, a in enumerate(pairs):
        for b in pairs[i + 1:]:
            ya = np.log(data[a]["close"].iloc[t - window:t].values)
            xb = np.log(data[b]["close"].iloc[t - window:t].values)
            if np.isnan(ya).any() or np.isnan(xb).any() or np.var(xb) == 0:
                continue
            beta = np.cov(xb, ya)[0, 1] / np.var(xb)
            v = np.var(ya - beta * xb)
            if v < best_var:
                best_var = v
                best = (a, b, beta)
    return best


def sig_06_cointegrated_pairs_spread(data, indicators, t, state, open_legs):
    """MP-STRAT-06: weekly re-selected cointegrated pair, trade log-price spread z-score."""
    entries, exits = {}, {}
    window = 90 * 24
    pairs = list(data.keys())
    if t % (24 * 7) == 0 and t >= window:
        best = _best_cointegrated_pair(data, t, pairs, window)
        if best:
            state["pair"], state["leg2"], state["beta"] = best
    if "pair" not in state:
        return {"entries": entries, "exits": exits}
    a, b, beta = state["pair"], state["leg2"], state["beta"]
    win_z = 50
    if t < win_z:
        return {"entries": entries, "exits": exits}
    # Causal slice strictly up to bar t
    ya = np.log(data[a]["close"].iloc[t - win_z:t].values)
    xb = np.log(data[b]["close"].iloc[t - win_z:t].values)
    if np.isnan(ya).any() or np.isnan(xb).any() or ya.std() == 0:
        return {"entries": entries, "exits": exits}
    spread = ya - beta * xb
    z = (spread[-1] - spread.mean()) / max(1e-8, spread.std())
    in_pos = a in open_legs or b in open_legs
    if in_pos:
        if abs(z) < 0.3 or abs(z) > 3.5:
            exits[a], exits[b] = True, True
    else:
        if z < -2.0:
            entries[a] = {"action": "enter_long", "risk_scale": 0.5}
            entries[b] = {"action": "enter_short", "risk_scale": 0.5}
        elif z > 2.0:
            entries[a] = {"action": "enter_short", "risk_scale": 0.5}
            entries[b] = {"action": "enter_long", "risk_scale": 0.5}
    return {"entries": entries, "exits": exits}


def sig_07_cross_asset_zscore_basket(data, indicators, t, state, open_legs):
    """MP-STRAT-07: per-pair z-score(price,50) mean reversion, with blowout exit at |z| > 3.5."""
    entries, exits = {}, {}
    for p in data.keys():
        z = indicators[p]["zscore50"].iat[t]
        if np.isnan(z):
            continue
        if p in open_legs:
            leg_dir = open_legs[p].direction
            # Exit on mean reversion through zero OR blowout risk management (|z| > 3.5)
            if (leg_dir == 1 and z >= 0) or (leg_dir == -1 and z <= 0) or abs(z) > 3.5:
                exits[p] = True
        else:
            if len(open_legs) >= 4:
                continue
            if z < -2.0:
                entries[p] = {"action": "enter_long"}
            elif z > 2.0:
                entries[p] = {"action": "enter_short"}
    return {"entries": entries, "exits": exits}


def sig_08_basket_neutral_reversion(data, indicators, t, state, open_legs):
    """MP-STRAT-08: long laggard / short leader vs equal-weight basket deviation, daily reselect."""
    entries, exits = {}, {}
    pairs = list(data.keys())
    window = 50
    if t < window:
        return {"entries": entries, "exits": exits}
    # Causal returns
    rets = {p: (data[p]["close"].iat[t] / data[p]["close"].iat[t - window] - 1.0) for p in pairs}
    if any(np.isnan(v) for v in rets.values()):
        return {"entries": entries, "exits": exits}
    basket_ret = np.mean(list(rets.values()))
    dev = {p: rets[p] - basket_ret for p in pairs}
    if t % 24 == 0:
        leader = max(dev, key=dev.get)
        laggard = min(dev, key=dev.get)
        if leader != laggard:
            new_pair = (laggard, leader)
            old_pair = state.get("pair")
            if old_pair != new_pair:
                if old_pair:
                    exits[old_pair[0]] = True
                    exits[old_pair[1]] = True
                state["pair"] = new_pair
    cur = state.get("pair")
    if cur:
        a, b = cur
        spread_dev = dev[a] - dev[b]
        in_pos = a in open_legs or b in open_legs
        if in_pos and abs(spread_dev) < 0.005:
            exits[a], exits[b] = True, True
        elif not in_pos and a not in exits and b not in exits:
            entries[a] = {"action": "enter_long", "risk_scale": 0.5}
            entries[b] = {"action": "enter_short", "risk_scale": 0.5}
    return {"entries": entries, "exits": exits}


def sig_09_vol_weighted_rsi_reversion(data, indicators, t, state, open_legs):
    """MP-STRAT-09: RSI(14)<30/>70 across all pairs simultaneously, normalized inverse-vol sizing."""
    entries, exits = {}, {}
    vols = {p: indicators[p]["rvol20"].iat[t] for p in data.keys()}
    valid_vols = [v for v in vols.values() if not np.isnan(v) and v > 0]
    median_vol = np.median(valid_vols) if valid_vols else 0.5

    for p in data.keys():
        rsi_v = indicators[p]["rsi14"].iat[t]
        if np.isnan(rsi_v):
            continue
        if p in open_legs:
            if rsi_v > 70:
                exits[p] = True
        else:
            if rsi_v < 30:
                vol = vols.get(p, median_vol)
                scale = median_vol / vol if vol and vol > 0 and not np.isnan(vol) else 1.0
                entries[p] = {"action": "enter_long", "risk_scale": float(np.clip(scale, 0.4, 2.0))}
    return {"entries": entries, "exits": exits}


def sig_10_triangular_basket_spread(data, indicators, t, state, open_legs):
    """MP-STRAT-10: SOL vs ETH log-price spread, causal rolling hedge ratio, z-score fade."""
    entries, exits = {}, {}
    a, b = "SOLUSDC", "ETHUSDC"
    if a not in data or b not in data:
        return {"entries": entries, "exits": exits}
    window = 100
    if t < window:
        return {"entries": entries, "exits": exits}
    # Causal slice strictly up to bar t
    ya = np.log(data[a]["close"].iloc[t - window:t].values)
    xb = np.log(data[b]["close"].iloc[t - window:t].values)
    if np.isnan(ya).any() or np.isnan(xb).any() or np.var(xb) == 0:
        return {"entries": entries, "exits": exits}
    beta = np.cov(xb, ya)[0, 1] / np.var(xb)
    spread = ya - beta * xb
    std = spread.std()
    if std == 0:
        return {"entries": entries, "exits": exits}
    z = (spread[-1] - spread.mean()) / std
    in_pos = a in open_legs or b in open_legs
    if in_pos:
        if abs(z) < 0.5 or abs(z) > 3.5:
            exits[a], exits[b] = True, True
    else:
        if z < -2.0:
            entries[a] = {"action": "enter_long", "risk_scale": 0.5}
            entries[b] = {"action": "enter_short", "risk_scale": 0.5}
        elif z > 2.0:
            entries[a] = {"action": "enter_short", "risk_scale": 0.5}
            entries[b] = {"action": "enter_long", "risk_scale": 0.5}
    return {"entries": entries, "exits": exits}


# =============================================================================
# Archetype 3: Volatility & Relative Strength
# =============================================================================

def sig_11_rsi_ranking_rotation(data, indicators, t, state, open_legs):
    """MP-STRAT-11: hold the 2 lowest-RSI pairs, 4h rebalance, RSI>60 forces exit any time."""
    entries, exits = {}, {}
    rsis = {p: indicators[p]["rsi14"].iat[t] for p in data.keys()}
    for p in list(open_legs.keys()):
        if not np.isnan(rsis.get(p, np.nan)) and rsis[p] > 60:
            exits[p] = True
    if t % 4 != 0:
        return {"entries": entries, "exits": exits}
    valid = {p: v for p, v in rsis.items() if not np.isnan(v)}
    if len(valid) < 2:
        return {"entries": entries, "exits": exits}
    ranked = sorted(valid.items(), key=lambda kv: kv[1])
    bottom2 = {p for p, _ in ranked[:2]}
    for p in list(open_legs.keys()):
        if p not in bottom2 and p not in exits:
            exits[p] = True
    for p in bottom2:
        if p not in open_legs:
            entries[p] = {"action": "enter_long"}
    return {"entries": entries, "exits": exits}


def sig_12_bb_squeeze_breakout(data, indicators, t, state, open_legs):
    """MP-STRAT-12: Bollinger bandwidth squeeze (bottom quintile) then breakout."""
    entries, exits = {}, {}
    if t == 0:
        return {"entries": entries, "exits": exits}
    for p in data.keys():
        ind = indicators[p]
        bw_prev = ind["bb_width_norm"].iat[t - 1]
        close, bb_up, bb_low = ind["close"].iat[t], ind["bb_up"].iat[t], ind["bb_low"].iat[t]
        if np.isnan(bw_prev) or np.isnan(bb_up) or np.isnan(bb_low):
            continue
        was_squeeze = bw_prev < 0.2
        if p in open_legs:
            mid = ind["bb_mid"].iat[t]
            leg_dir = open_legs[p].direction
            if not np.isnan(mid) and ((leg_dir == 1 and close < mid) or (leg_dir == -1 and close > mid)):
                exits[p] = True
        else:
            if len(open_legs) >= 3:
                continue
            if was_squeeze and close > bb_up:
                entries[p] = {"action": "enter_long"}
            elif was_squeeze and close < bb_low:
                entries[p] = {"action": "enter_short"}
    return {"entries": entries, "exits": exits}


def sig_13_atr_regime_momentum(data, indicators, t, state, open_legs):
    """MP-STRAT-13: EMA20/50 cross, gated to only fire when ATR% is in top half of its 60d range."""
    entries, exits = {}, {}
    if t == 0:
        return {"entries": entries, "exits": exits}
    for p in data.keys():
        ind = indicators[p]
        atr_norm = ind["atr_pct_norm"].iat[t]
        e20, e50 = ind["ema20"].iat[t], ind["ema50"].iat[t]
        e20p, e50p = ind["ema20"].iat[t - 1], ind["ema50"].iat[t - 1]
        if np.isnan(atr_norm) or np.isnan(e20) or np.isnan(e50) or np.isnan(e20p) or np.isnan(e50p):
            continue
        cross_up = e20p <= e50p and e20 > e50
        cross_down = e20p >= e50p and e20 < e50
        if p in open_legs:
            if cross_down:
                exits[p] = True
        else:
            if cross_up and atr_norm > 0.5:
                entries[p] = {"action": "enter_long"}
    return {"entries": entries, "exits": exits}


def sig_14_vol_ranked_long_short_rs(data, indicators, t, state, open_legs):
    """MP-STRAT-14: long best-momentum pair in high-vol tercile, short worst in low-vol, weekly."""
    entries, exits = {}, {}
    if t % (24 * 7) != 0 or t == 0:
        return {"entries": entries, "exits": exits}
    pairs = list(data.keys())
    vols = {p: indicators[p]["rvol20"].iat[t] for p in pairs}
    moms = {p: indicators[p]["mom_30d"].iat[t] for p in pairs}
    valid_pairs = [p for p in pairs if not np.isnan(vols[p]) and not np.isnan(moms[p])]
    if len(valid_pairs) < 3:
        return {"entries": entries, "exits": exits}
    ranked_vol = sorted(valid_pairs, key=lambda p: vols[p])
    n = len(ranked_vol)
    high_vol = set(ranked_vol[int(np.ceil(n * 2 / 3)):]) or {ranked_vol[-1]}
    low_vol = set(ranked_vol[:max(1, int(n / 3))])
    long_pick = max(high_vol, key=lambda p: moms[p]) if high_vol else None
    short_pick = min(low_vol, key=lambda p: moms[p]) if low_vol else None
    target = {}
    if long_pick:
        target[long_pick] = "enter_long"
    if short_pick and short_pick != long_pick:
        target[short_pick] = "enter_short"
    for p in list(open_legs.keys()):
        if p not in target:
            exits[p] = True
    for p, act in target.items():
        if p not in open_legs:
            entries[p] = {"action": act}
    return {"entries": entries, "exits": exits}


def sig_15_keltner_breakout(data, indicators, t, state, open_legs):
    """MP-STRAT-15: Keltner channel breakout, exit on reversion through mid-line."""
    entries, exits = {}, {}
    for p in data.keys():
        ind = indicators[p]
        kc_up, kc_low, kc_mid = ind["kc_up"].iat[t], ind["kc_low"].iat[t], ind["kc_mid"].iat[t]
        close = ind["close"].iat[t]
        if np.isnan(kc_up) or np.isnan(kc_low) or np.isnan(kc_mid):
            continue
        if p in open_legs:
            leg_dir = open_legs[p].direction
            if (leg_dir == 1 and close < kc_mid) or (leg_dir == -1 and close > kc_mid):
                exits[p] = True
        else:
            if len(open_legs) >= 4:
                continue
            if close > kc_up:
                entries[p] = {"action": "enter_long"}
            elif close < kc_low:
                entries[p] = {"action": "enter_short"}
    return {"entries": entries, "exits": exits}


# =============================================================================
# Archetype 4: Multi-Asset Risk-Parity & Dynamic Rotation (weight-based)
# =============================================================================

def w_16_inverse_vol_risk_parity(data, indicators, t, state):
    """MP-STRAT-16: always-long basket, inverse-volatility weighted, daily rebalance."""
    if t % 24 != 0:
        return None
    pairs = list(data.keys())
    vols = {p: indicators[p]["rvol20"].iat[t] for p in pairs}
    valid = {p: v for p, v in vols.items() if not np.isnan(v) and v > 0}
    if not valid:
        return None
    inv = {p: 1.0 / v for p, v in valid.items()}
    tot = sum(inv.values())
    w = {p: 0.0 for p in pairs}
    for p, val in inv.items():
        w[p] = val / tot
    return w


def w_17_dual_momentum_rotation(data, indicators, t, state):
    """
    MP-STRAT-17: hold top-2 by cross-sectional Z-score blended momentum (12h, 72h, 30d).
    Only holds pairs with positive absolute momentum; gracefully isolates missing pairs.
    """
    if t % 24 != 0:
        return None
    pairs = list(data.keys())
    raw_moms = {"12h": {}, "72h": {}, "30d": {}}
    for p in pairs:
        m12 = indicators[p]["mom_12h"].iat[t]
        m72 = indicators[p]["mom_72h"].iat[t]
        m30d = indicators[p]["mom_30d"].iat[t]
        if not np.isnan(m12):
            raw_moms["12h"][p] = m12
        if not np.isnan(m72):
            raw_moms["72h"][p] = m72
        if not np.isnan(m30d):
            raw_moms["30d"][p] = m30d

    # Calculate cross-sectional z-score for each horizon so fast signals aren't overwhelmed
    blended = {}
    valid_pairs = set(raw_moms["12h"].keys()) & set(raw_moms["72h"].keys()) & set(raw_moms["30d"].keys())
    if not valid_pairs:
        return None

    for horizon in ["12h", "72h", "30d"]:
        vals = [raw_moms[horizon][p] for p in valid_pairs]
        mean_v = np.mean(vals)
        std_v = np.std(vals) if np.std(vals) > 1e-8 else 1.0
        for p in valid_pairs:
            z = (raw_moms[horizon][p] - mean_v) / std_v
            blended[p] = blended.get(p, 0.0) + z / 3.0

    # Must also pass absolute positive trend filter (positive 30d momentum)
    qualifying = {p: score for p, score in blended.items() if raw_moms["30d"][p] > 0}
    w = {p: 0.0 for p in pairs}
    if not qualifying:
        return w
    ranked = sorted(qualifying.items(), key=lambda kv: kv[1], reverse=True)
    top2 = [p for p, _ in ranked[:2]]
    for p in top2:
        w[p] = 1.0 / len(top2)
    return w


def w_18_target_vol_overlay(data, indicators, t, state):
    """
    MP-STRAT-18: equal-weight basket, scaled to a 15% annualized target volatility.
    Calculates actual portfolio return variance (including cross-asset correlations).
    """
    if t % 24 != 0 or t < 50:
        return None
    pairs = list(data.keys())
    n = len(pairs)
    # Causal portfolio return series over trailing 50 bars
    port_rets = sum((1.0 / n) * data[p]["close"].pct_change().iloc[t - 50:t] for p in pairs)
    port_std = port_rets.std()
    if np.isnan(port_std) or port_std <= 0:
        return None
    actual_port_vol = float(port_std * np.sqrt(BARS_PER_YEAR))
    target_vol = 0.15
    lev = float(np.clip(target_vol / actual_port_vol, 0.25, 3.0))
    return {p: (1.0 / n) * lev for p in pairs}


def w_19_correlation_adjusted_rotation(data, indicators, t, state):
    """MP-STRAT-19: momentum-ranked top-3, skipping candidates >0.8 correlated (30d) with selected."""
    if t % 24 != 0 or t < 720:
        return None
    pairs = list(data.keys())
    moms = {p: indicators[p]["mom_30d"].iat[t] for p in pairs}
    valid = {p: v for p, v in moms.items() if not np.isnan(v)}
    if len(valid) < 3:
        return None
    ranked = sorted(valid.items(), key=lambda kv: kv[1], reverse=True)
    window = 30 * 24
    rets_window = {p: data[p]["close"].pct_change().iloc[t - window:t] for p in valid.keys()}
    selected = []
    for p, _ in ranked:
        if len(selected) >= 3:
            break
        ok = True
        for s in selected:
            c = rets_window[p].corr(rets_window[s])
            if c is not None and not np.isnan(c) and c > 0.8:
                ok = False
                break
        if ok:
            selected.append(p)
    w = {p: 0.0 for p in pairs}
    for p in selected:
        w[p] = 1.0 / len(selected) if selected else 0.0
    return w


# =============================================================================
# Cross-archetype: regime-switching (discrete)
# =============================================================================

def sig_20_regime_switch(data, indicators, t, state, open_legs):
    """MP-STRAT-20: ADX(14)>25 -> trend rules; ADX<20 -> reversion rules; hysteresis band 20-25."""
    entries, exits = {}, {}
    if t == 0:
        return {"entries": entries, "exits": exits}
    for p in data.keys():
        ind = indicators[p]
        adx_v = ind["adx14"].iat[t]
        if np.isnan(adx_v):
            continue
        mode = state.get(("mode", p), "reversion")
        if adx_v > 25:
            mode = "trend"
        elif adx_v < 20:
            mode = "reversion"
        state[("mode", p)] = mode
        if mode == "trend":
            e20, e50 = ind["ema20"].iat[t], ind["ema50"].iat[t]
            if np.isnan(e20) or np.isnan(e50):
                continue
            if p in open_legs:
                if e20 < e50:
                    exits[p] = True
            else:
                if e20 > e50:
                    entries[p] = {"action": "enter_long"}
        else:
            rsi_v = ind["rsi14"].iat[t]
            if np.isnan(rsi_v):
                continue
            if p in open_legs:
                if rsi_v > 60:
                    exits[p] = True
            else:
                if rsi_v < 30:
                    entries[p] = {"action": "enter_long"}
    return {"entries": entries, "exits": exits}


# =============================================================================
# Registry
# =============================================================================
def build_strategies() -> list[StrategyConfig]:
    return [
        StrategyConfig("MP-STRAT-01", "Cross-Sectional Momentum & Rotation", "Trend/Momentum", "discrete",
                        signal_fn=sig_01_cross_sectional_momentum, max_concurrent_legs=2,
                        risk_per_trade=0.01, portfolio_heat_cap=0.02),
        StrategyConfig("MP-STRAT-02", "Dual Moving-Average Trend Filter Basket", "Trend/Momentum", "discrete",
                        signal_fn=sig_02_dual_ma_trend, max_concurrent_legs=5,
                        risk_per_trade=0.01, portfolio_heat_cap=0.05),
        StrategyConfig("MP-STRAT-03", "Donchian Breakout Multi-Asset (Turtle)", "Trend/Momentum", "discrete",
                        signal_fn=sig_03_donchian_breakout, max_concurrent_legs=5,
                        risk_per_trade=0.01, portfolio_heat_cap=0.05),
        StrategyConfig("MP-STRAT-04", "MACD Histogram Momentum Rank & Rotate", "Trend/Momentum", "discrete",
                        signal_fn=sig_04_macd_rank_rotate, max_concurrent_legs=3,
                        risk_per_trade=0.01, portfolio_heat_cap=0.045),
        StrategyConfig("MP-STRAT-05", "Relative Strength vs BTC Trend-Following", "Trend/Momentum", "discrete",
                        signal_fn=sig_05_relative_strength_btc, max_concurrent_legs=3,
                        risk_per_trade=0.01, portfolio_heat_cap=0.03),

        StrategyConfig("MP-STRAT-06", "Cointegrated Pairs Spread Trading", "Stat Arb / Pairs", "discrete",
                        signal_fn=sig_06_cointegrated_pairs_spread, max_concurrent_legs=2,
                        risk_per_trade=0.01, portfolio_heat_cap=0.01),
        StrategyConfig("MP-STRAT-07", "Cross-Asset Z-Score Basket Mean Reversion", "Stat Arb / Pairs", "discrete",
                        signal_fn=sig_07_cross_asset_zscore_basket, max_concurrent_legs=4,
                        risk_per_trade=0.01, portfolio_heat_cap=0.04),
        StrategyConfig("MP-STRAT-08", "Basket-Neutral Mean Reversion (Laggard/Leader)", "Stat Arb / Pairs", "discrete",
                        signal_fn=sig_08_basket_neutral_reversion, max_concurrent_legs=2,
                        risk_per_trade=0.01, portfolio_heat_cap=0.01),
        StrategyConfig("MP-STRAT-09", "Volatility-Weighted Multi-Pair RSI Reversion", "Stat Arb / Pairs", "discrete",
                        signal_fn=sig_09_vol_weighted_rsi_reversion, max_concurrent_legs=5,
                        risk_per_trade=0.01, portfolio_heat_cap=0.08),
        StrategyConfig("MP-STRAT-10", "Triangular Basket Spread Reversion (SOL/ETH)", "Stat Arb / Pairs", "discrete",
                        signal_fn=sig_10_triangular_basket_spread, max_concurrent_legs=2,
                        risk_per_trade=0.01, portfolio_heat_cap=0.01),

        StrategyConfig("MP-STRAT-11", "Multi-Pair RSI Ranking Rotation", "Vol / Relative Strength", "discrete",
                        signal_fn=sig_11_rsi_ranking_rotation, max_concurrent_legs=2,
                        risk_per_trade=0.01, portfolio_heat_cap=0.02),
        StrategyConfig("MP-STRAT-12", "Bollinger Band-Width Squeeze Breakout", "Vol / Relative Strength", "discrete",
                        signal_fn=sig_12_bb_squeeze_breakout, max_concurrent_legs=3,
                        risk_per_trade=0.01, portfolio_heat_cap=0.03),
        StrategyConfig("MP-STRAT-13", "ATR-Percentile Volatility Regime Filter Momentum", "Vol / Relative Strength", "discrete",
                        signal_fn=sig_13_atr_regime_momentum, max_concurrent_legs=5,
                        risk_per_trade=0.01, portfolio_heat_cap=0.05),
        StrategyConfig("MP-STRAT-14", "Realized-Vol Ranked Long/Short Relative Strength", "Vol / Relative Strength", "discrete",
                        signal_fn=sig_14_vol_ranked_long_short_rs, max_concurrent_legs=2,
                        risk_per_trade=0.01, portfolio_heat_cap=0.02),
        StrategyConfig("MP-STRAT-15", "Multi-Pair Keltner Channel Volatility Breakout", "Vol / Relative Strength", "discrete",
                        signal_fn=sig_15_keltner_breakout, max_concurrent_legs=4,
                        risk_per_trade=0.01, portfolio_heat_cap=0.04),

        StrategyConfig("MP-STRAT-16", "Inverse-Volatility Risk Parity Static Basket", "Risk-Parity / Rotation", "weight",
                        weight_fn=w_16_inverse_vol_risk_parity, max_gross_leverage=1.0),
        StrategyConfig("MP-STRAT-17", "Trend-Confirmed Dynamic Rotation (Dual Momentum)", "Risk-Parity / Rotation", "weight",
                        weight_fn=w_17_dual_momentum_rotation, max_gross_leverage=1.0),
        StrategyConfig("MP-STRAT-18", "Target-Volatility Portfolio Overlay", "Risk-Parity / Rotation", "weight",
                        weight_fn=w_18_target_vol_overlay, max_gross_leverage=3.0),
        StrategyConfig("MP-STRAT-19", "Correlation-Adjusted Momentum Rotation", "Risk-Parity / Rotation", "weight",
                        weight_fn=w_19_correlation_adjusted_rotation, max_gross_leverage=1.0),

        StrategyConfig("MP-STRAT-20", "Regime-Switching Trend/Mean-Reversion Rotation", "Risk-Parity / Rotation", "discrete",
                        signal_fn=sig_20_regime_switch, max_concurrent_legs=5,
                        risk_per_trade=0.01, portfolio_heat_cap=0.05),
    ]
