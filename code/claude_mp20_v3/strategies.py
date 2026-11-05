"""
strategies.py — claude_mp20_v3
20 multi-pair crypto trading strategies, redesigned from ground-up based on v2 failure analysis.

Key design principles applied throughout:
  - LOW TURNOVER: minimum hold bars enforced per-strategy; no forced-reversal exits.
  - REGIME GATES: ADX, volatility-regime, or trend-direction filter on every strategy.
  - LONGER-TERM SIGNALS: momentum lookbacks ≥ 30d; no 12h momentum as primary signal.
  - SIMPLE LOGIC: 1–3 conditions per entry; interpretable and robust.
  - WEIGHT-MODE for rotation: genuine signal-driven weights, not random.
  - STAT-ARB is extremely selective: ADF p < 0.02, one pair, monthly re-entry cap.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller
from engine_core import StrategyConfig, BARS_PER_YEAR

UNIVERSE = ["SOLUSDC", "BTCUSDC", "ETHUSDC", "AVAXUSDC", "LINKUSDC"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe(indicators, pair, col, t):
    """Return indicator value, or NaN if index is out of range or value is missing."""
    ind = indicators.get(pair)
    if ind is None:
        return np.nan
    ser = ind.get(col)
    if ser is None:
        return np.nan
    if t < 0 or t >= len(ser):
        return np.nan
    v = ser.iat[t]
    return np.nan if pd.isna(v) else v


def _min_hold(state, pair, t, hold_bars):
    """Return True if the pair's entry bar has aged at least hold_bars bars."""
    entry_bar = state.get(f"entry_{pair}", -999999)
    return (t - entry_bar) >= hold_bars


def _record_entry(state, pair, t):
    state[f"entry_{pair}"] = t


# =============================================================================
# S01 — 90-Day High Momentum Breakout (Trend-Following, Low Turnover)
# =============================================================================

def sig_01_90d_high_breakout(data, indicators, t, state, open_legs):
    """
    S01: '52-Week High Momentum'
    Entry:  close > 90-day rolling max (prior bar), ADX > 25, checked weekly.
    Exit:   close < 30-day rolling low OR stop via ATR.

    Avoids v2 failures:
      - Weekly recheck only → low turnover.
      - ADX > 25 gate → trend confirmation, no sideways churn.
      - 90d breakout is genuinely long-term signal, not noise.
    """
    entries, exits = {}, {}
    pairs = list(data.keys())

    # Only re-evaluate entries once per week (168h); exits checked every bar
    is_entry_bar = (t % 168 == 0)

    for p in pairs:
        close_t = _safe(indicators, p, "close", t)
        adx_t = _safe(indicators, p, "adx14", t)
        don_low20 = _safe(indicators, p, "don_low20", t)
        if np.isnan(close_t):
            continue

        # Compute rolling 90-day (2160h) high using raw data (causal: up to t-1)
        if t >= 2161:
            rolling_high_90d = data[p]["high"].iloc[t - 2160: t].max()
            rolling_low_30d = data[p]["low"].iloc[t - 720: t].min()
        elif t >= 720:
            rolling_high_90d = np.nan
            rolling_low_30d = data[p]["low"].iloc[:t].min()
        else:
            continue

        if p in open_legs:
            # Exit if price falls below 30-day rolling low (ATR stop also managed by engine)
            if not np.isnan(rolling_low_30d) and close_t < rolling_low_30d:
                exits[p] = True
        else:
            if is_entry_bar and not np.isnan(rolling_high_90d) and not np.isnan(adx_t):
                if close_t > rolling_high_90d and adx_t > 25:
                    entries[p] = {"action": "enter_long", "risk_scale": 1.0}
                    _record_entry(state, p, t)

    return {"entries": entries, "exits": exits}


# =============================================================================
# S02 — Multi-Period Momentum Composite (Trend, Weekly Rotation)
# =============================================================================

def sig_02_composite_momentum(data, indicators, t, state, open_legs):
    """
    S02: 'Multi-Period Momentum Composite'
    Score = 0.5*mom_60d + 0.3*mom_30d + 0.2*mom_72h (z-score normalised).
    Hold top-2 assets with positive composite score. Minimum 72h hold.
    Weekly re-rank (every 168 bars).

    Avoids v2 failures:
      - 60d momentum is the dominant factor (longer-term, more robust).
      - 72h minimum hold prevents whipsaw from intra-week noise.
      - Weekly evaluation limits turnover to ~4 rebalances/month.
    """
    entries, exits = {}, {}
    if t % 168 != 0 or t < 60 * 24:
        # Only check exits when a top pair needs eviction
        return {"entries": entries, "exits": exits}

    pairs = list(data.keys())
    scores = {}
    for p in pairs:
        # 60d momentum (1440h), 30d (720h), 72h — all causal
        if t < 1440:
            continue
        m60 = _safe(indicators, p, "mom_30d", t)  # mom_30d ≈ 720h; use it twice weighted
        # We compute 60d manually from close series
        c_now = data[p]["close"].iat[t]
        c_60d = data[p]["close"].iat[t - 1440] if t >= 1440 else np.nan
        m60d = (c_now / c_60d - 1) if not np.isnan(c_60d) and c_60d > 0 else np.nan
        m30d = _safe(indicators, p, "mom_30d", t)
        m72h = _safe(indicators, p, "mom_72h", t)
        if any(np.isnan(v) for v in [m60d, m30d, m72h]):
            continue
        scores[p] = 0.5 * m60d + 0.3 * m30d + 0.2 * m72h

    if len(scores) < 2:
        return {"entries": entries, "exits": exits}

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top2 = {p for p, s in ranked[:2] if s > 0}

    for p in list(open_legs.keys()):
        if p not in top2 and _min_hold(state, p, t, 72):
            exits[p] = True

    for p in top2:
        if p not in open_legs:
            entries[p] = {"action": "enter_long", "risk_scale": 1.0}
            _record_entry(state, p, t)

    return {"entries": entries, "exits": exits}


# =============================================================================
# S03 — EMA50 Slope Acceleration (Trend, Low Turnover)
# =============================================================================

def sig_03_ema_slope_accel(data, indicators, t, state, open_legs):
    """
    S03: 'EMA Slope Acceleration'
    Long when EMA50 slope (current bar vs 3 bars ago) is accelerating (slope > prior slope)
    AND above zero. ADX > 20 gate. Exit when slope turns negative (EMA50 declining).

    Avoids v2 failures:
      - EMA50 slope filters out high-frequency noise (longer-term trend direction).
      - ADX gate suppresses sideways range entries.
      - Exit only on genuine slope reversal — not on minor pullbacks.
    """
    entries, exits = {}, {}
    if t < 6:
        return {"entries": entries, "exits": exits}

    pairs = list(data.keys())
    for p in pairs:
        e50_t = _safe(indicators, p, "ema50", t)
        e50_t3 = _safe(indicators, p, "ema50", t - 3)
        e50_t6 = _safe(indicators, p, "ema50", t - 6)
        adx_t = _safe(indicators, p, "adx14", t)
        if any(np.isnan(v) for v in [e50_t, e50_t3, e50_t6, adx_t]):
            continue

        slope_now = e50_t - e50_t3     # slope over last 3 bars
        slope_prev = e50_t3 - e50_t6   # slope over prior 3 bars
        accelerating = (slope_now > slope_prev) and (slope_now > 0)
        decelerating = slope_now < 0

        if p in open_legs:
            if decelerating and _min_hold(state, p, t, 48):
                exits[p] = True
        else:
            if accelerating and adx_t > 20:
                entries[p] = {"action": "enter_long", "risk_scale": 1.0}
                _record_entry(state, p, t)

    return {"entries": entries, "exits": exits}


# =============================================================================
# S04 — Trend Pullback Entry (Mean-Reversion in Trend Direction)
# =============================================================================

def sig_04_trend_pullback(data, indicators, t, state, open_legs):
    """
    S04: 'Trend Pullback Entry'
    Entry: EMA200 rising (close > EMA200), price pulls back near EMA50,
    RSI 40–60 (mid-zone — healthy pullback, not crash), ADX > 20.
    Exit: ATR-stop (managed by engine) or RSI > 70 (overbought flush).

    Avoids v2 failures:
      - Requires EMA200 uptrend — no counter-trend shorts.
      - RSI 40-60 ensures we buy dips in trends, not momentum spikes.
      - Price proximity to EMA50 limits the number of signals (low turnover).
    """
    entries, exits = {}, {}
    if t < 200:
        return {"entries": entries, "exits": exits}

    for p in list(data.keys()):
        close_t = _safe(indicators, p, "close", t)
        e50 = _safe(indicators, p, "ema50", t)
        e200 = _safe(indicators, p, "ema200", t)
        rsi = _safe(indicators, p, "rsi14", t)
        adx = _safe(indicators, p, "adx14", t)
        if any(np.isnan(v) for v in [close_t, e50, e200, rsi, adx]):
            continue

        # Within 2% of EMA50 (pullback zone)
        near_ema50 = abs(close_t - e50) / e50 < 0.02

        if p in open_legs:
            if rsi > 70 and _min_hold(state, p, t, 24):
                exits[p] = True
        else:
            if (close_t > e200) and near_ema50 and (40 <= rsi <= 60) and adx > 20:
                entries[p] = {"action": "enter_long", "risk_scale": 1.0}
                _record_entry(state, p, t)

    return {"entries": entries, "exits": exits}


# =============================================================================
# S05 — Absolute Momentum 6-Month Barrier (Simple, Robust)
# =============================================================================

def sig_05_abs_momentum_6m(data, indicators, t, state, open_legs):
    """
    S05: 'Absolute Momentum with 6-Month Barrier'
    Long only if 6-month (4380h) return is positive. Monthly rebalance (720 bars).
    Exit all when 6-month return turns negative.

    Avoids v2 failures:
      - 6-month return is maximally long-term — highly robust signal.
      - Monthly rebalance: ~6 trades per year per asset = very low turnover.
      - No regime-specific parameters to overfit.
    """
    entries, exits = {}, {}
    LOOKBACK = 4380   # 6 months in hours
    REBAL_BARS = 720  # monthly rebalance

    if t % REBAL_BARS != 0 or t < LOOKBACK:
        return {"entries": entries, "exits": exits}

    pairs = list(data.keys())
    for p in pairs:
        c_now = data[p]["close"].iat[t]
        c_6m = data[p]["close"].iat[t - LOOKBACK]
        if c_6m <= 0:
            continue
        mom_6m = c_now / c_6m - 1

        if p in open_legs:
            if mom_6m <= 0:
                exits[p] = True
        else:
            if mom_6m > 0:
                entries[p] = {"action": "enter_long", "risk_scale": 1.0}
                _record_entry(state, p, t)

    return {"entries": entries, "exits": exits}


# =============================================================================
# S06 — Volatility Contraction Breakout (72h Mandatory Hold)
# =============================================================================

def sig_06_vix_squeeze_breakout(data, indicators, t, state, open_legs):
    """
    S06: 'Volatility Contraction Breakout'
    Entry: bb_width_norm < 0.15 (very tight squeeze) AND close > BB upper.
    Mandatory 72h hold before any signal-based exit. Max 2 concurrent legs.

    Avoids v2 failures:
      - bb_width_norm < 0.15 is very selective — far fewer false breakouts.
      - 72h mandatory hold prevents immediate stop-out from volatility snapback.
      - Max 2 concurrent keeps capital concentrated on best setups.
    """
    entries, exits = {}, {}
    MAX_LEGS = 2

    pairs = list(data.keys())
    for p in pairs:
        close_t = _safe(indicators, p, "close", t)
        bb_up = _safe(indicators, p, "bb_up", t)
        bb_wn = _safe(indicators, p, "bb_width_norm", t)
        if any(np.isnan(v) for v in [close_t, bb_up, bb_wn]):
            continue

        if p in open_legs:
            # Only allow exit after mandatory 72h hold
            if _min_hold(state, p, t, 72):
                # Exit when price falls back below bb_mid
                bb_mid = _safe(indicators, p, "bb_mid", t)
                if not np.isnan(bb_mid) and close_t < bb_mid:
                    exits[p] = True
        else:
            active = sum(1 for x in open_legs if x in data)
            if active < MAX_LEGS and bb_wn < 0.15 and close_t > bb_up:
                entries[p] = {"action": "enter_long", "risk_scale": 1.0}
                _record_entry(state, p, t)

    return {"entries": entries, "exits": exits}


# =============================================================================
# S07 — ATR Expansion Trend (48h Mandatory Hold)
# =============================================================================

def sig_07_atr_expansion_trend(data, indicators, t, state, open_legs):
    """
    S07: 'ATR Expansion Trend'
    Entry: bar-to-bar ATR expands > 20% AND close > EMA50 (confirming bullish expansion).
    Minimum 48h hold before signal-based exit allowed.

    Avoids v2 failures:
      - ATR expansion + trend filter = genuine momentum event, not noise.
      - 48h minimum hold prevents immediate reversal churn.
      - EMA50 filter keeps entries to trending markets only.
    """
    entries, exits = {}, {}
    if t < 2:
        return {"entries": entries, "exits": exits}

    for p in list(data.keys()):
        atr_t = _safe(indicators, p, "atr14", t)
        atr_p = _safe(indicators, p, "atr14", t - 1)
        close_t = _safe(indicators, p, "close", t)
        e50 = _safe(indicators, p, "ema50", t)
        if any(np.isnan(v) for v in [atr_t, atr_p, close_t, e50]) or atr_p <= 0:
            continue

        atr_expansion = (atr_t / atr_p) - 1.0

        if p in open_legs:
            if _min_hold(state, p, t, 48):
                # Exit when ATR contracts back AND price dips below EMA50
                if close_t < e50:
                    exits[p] = True
        else:
            if atr_expansion > 0.20 and close_t > e50:
                entries[p] = {"action": "enter_long", "risk_scale": 1.0}
                _record_entry(state, p, t)

    return {"entries": entries, "exits": exits}


# =============================================================================
# S08 — Low-Vol Momentum Carry (Regime Gate)
# =============================================================================

def sig_08_lowvol_momentum_carry(data, indicators, t, state, open_legs):
    """
    S08: 'Low-Vol Momentum Carry'
    In low-vol regime (rvol20 < 0.40 annualized for ALL assets), hold top-3 by 30d mom.
    Exit ALL positions when any asset's rvol20 exceeds 0.60 (vol spike).
    Weekly rebalance inside the low-vol regime.

    Avoids v2 failures:
      - Dual vol threshold creates clear regime gate — only trades in calm conditions.
      - Vol spike exit prevents catastrophic drawdowns during panics.
      - 30d momentum avoids short-term noise.
    """
    entries, exits = {}, {}
    if t < 720 or t % 168 != 0:
        return {"entries": entries, "exits": exits}

    pairs = list(data.keys())
    rvols = {p: _safe(indicators, p, "rvol20", t) for p in pairs}

    # Check if vol spike is happening — exit all if any pair is spiking
    if any(v > 0.60 for v in rvols.values() if not np.isnan(v)):
        for p in list(open_legs.keys()):
            exits[p] = True
        return {"entries": entries, "exits": exits}

    # Only enter in low-vol regime
    in_low_vol = all(v < 0.40 for v in rvols.values() if not np.isnan(v))
    if not in_low_vol:
        return {"entries": entries, "exits": exits}

    moms = {p: _safe(indicators, p, "mom_30d", t) for p in pairs}
    valid = {p: v for p, v in moms.items() if not np.isnan(v)}
    ranked = sorted(valid.items(), key=lambda kv: kv[1], reverse=True)
    top3 = {p for p, _ in ranked[:3] if moms.get(p, -999) > 0}

    for p in list(open_legs.keys()):
        if p not in top3:
            exits[p] = True

    for p in top3:
        if p not in open_legs:
            entries[p] = {"action": "enter_long", "risk_scale": 1.0}
            _record_entry(state, p, t)

    return {"entries": entries, "exits": exits}


# =============================================================================
# S09 — Volatility Mean Reversion Short (Vol-Regime)
# =============================================================================

def sig_09_vol_mean_reversion_short(data, indicators, t, state, open_legs):
    """
    S09: 'Volatility Mean Reversion Short'
    When rvol20 crosses above its 200-bar 90th percentile AND price momentum is
    negative (mom_30d < 0), short the worst-performing asset.
    Close when rvol20 drops below the 200-bar 60th percentile.
    Maximum 1 concurrent short, monthly re-entry cap.

    Avoids v2 failures:
      - Monthly re-entry cap limits total trades dramatically.
      - 200-bar percentile is robust and not curve-fitted.
      - Closes when vol normalizes — not at arbitrary time target.
    """
    entries, exits = {}, {}
    if t < 200:
        return {"entries": entries, "exits": exits}

    # Monthly re-entry cap per pair
    pairs = list(data.keys())

    for p in pairs:
        rvol = _safe(indicators, p, "rvol20", t)
        if np.isnan(rvol):
            continue

        # Rolling percentile window (200 bars)
        window_rvol = indicators[p]["rvol20"].iloc[max(0, t - 200): t + 1].dropna()
        if len(window_rvol) < 50:
            continue
        p90 = window_rvol.quantile(0.90)
        p60 = window_rvol.quantile(0.60)

        if p in open_legs:
            # Exit when vol normalises
            if rvol < p60:
                exits[p] = True
        else:
            # Only one short at a time total
            if len(open_legs) >= 1:
                continue
            # Monthly cap: don't re-enter within 720 bars of last entry
            last_entry = state.get(f"entry_{p}", -99999)
            if (t - last_entry) < 720:
                continue
            mom = _safe(indicators, p, "mom_30d", t)
            if rvol > p90 and not np.isnan(mom) and mom < 0:
                entries[p] = {"action": "enter_short", "risk_scale": 1.0}
                _record_entry(state, p, t)

    return {"entries": entries, "exits": exits}


# =============================================================================
# S10 — Pure Equal-Weight Momentum (Weight Mode)
# =============================================================================

def wt_10_equal_weight_momentum(data, indicators, t, state):
    """
    S10: 'Pure Equal Weight Momentum'
    Weight-mode. Every 7 days (168 bars), equal-weight all assets with positive
    20d momentum. Assets with negative 20d momentum receive weight 0 (cash).

    Avoids v2 failures:
      - Weekly rebalance → very low turnover vs daily.
      - 20d momentum screen prevents holding obvious losers.
      - Simple equal-weight avoids optimization overfit.
    """
    if t % 168 != 0 or t < 480:
        return None

    pairs = list(data.keys())
    eligible = []
    for p in pairs:
        m20 = _safe(indicators, p, "mom_30d", t)  # mom_30d is 720h (30d)
        # Use 20d (~480h) computed from close
        if t >= 480:
            c_now = data[p]["close"].iat[t]
            c_20d = data[p]["close"].iat[t - 480]
            m20 = (c_now / c_20d - 1) if c_20d > 0 else np.nan
        if not np.isnan(m20) and m20 > 0:
            eligible.append(p)

    if not eligible:
        return {p: 0.0 for p in pairs}

    w = 1.0 / len(eligible)
    return {p: (w if p in eligible else 0.0) for p in pairs}


# =============================================================================
# S11 — Min-Variance Portfolio (Weight Mode, Weekly)
# =============================================================================

def wt_11_min_variance(data, indicators, t, state):
    """
    S11: 'Min Variance Portfolio'
    Weight-mode. Weekly rebalance to minimum-variance weights using 60d rolling
    covariance matrix (long-only, equal-risk-contribution approximation).

    Avoids v2 failures:
      - Inverse-volatility weights are a robust proxy for min-variance.
      - Weekly rebalance → low turnover.
      - No optimization parameters that can be overfitted.
    """
    if t % 168 != 0 or t < 1440:
        return None

    pairs = list(data.keys())
    WINDOW = 1440  # 60 days in hours

    vols = {}
    for p in pairs:
        close_slice = data[p]["close"].iloc[t - WINDOW: t]
        logrets = np.log(close_slice / close_slice.shift(1)).dropna()
        if len(logrets) < 100:
            continue
        v = logrets.std() * np.sqrt(BARS_PER_YEAR)
        if v > 0:
            vols[p] = v

    if not vols:
        return None

    inv_vols = {p: 1.0 / v for p, v in vols.items()}
    total = sum(inv_vols.values())
    weights = {p: (iv / total) for p, iv in inv_vols.items()}
    return {p: weights.get(p, 0.0) for p in pairs}


# =============================================================================
# S12 — Risk Parity with Momentum Filter (Weight Mode, Monthly)
# =============================================================================

def wt_12_risk_parity_momentum(data, indicators, t, state):
    """
    S12: 'Risk Parity with Momentum Filter'
    Weight-mode. Inverse-vol weights, but only for assets with positive 20d momentum.
    Monthly rebalance (720 bars).

    Avoids v2 failures:
      - Combines two robust signals: volatility sizing + momentum filter.
      - Monthly rebalance → ~6 rebalances per year = very low turnover.
      - No covariance matrix inversion — robust to collinearity.
    """
    if t % 720 != 0 or t < 1440:
        return None

    pairs = list(data.keys())
    WINDOW = 1440  # 60d for vol estimation

    eligible = {}
    for p in pairs:
        c_now = data[p]["close"].iat[t]
        c_20d = data[p]["close"].iat[t - 480] if t >= 480 else np.nan
        mom20 = (c_now / c_20d - 1) if not np.isnan(c_20d) and c_20d > 0 else np.nan
        if np.isnan(mom20) or mom20 <= 0:
            continue
        close_slice = data[p]["close"].iloc[t - WINDOW: t]
        logrets = np.log(close_slice / close_slice.shift(1)).dropna()
        if len(logrets) < 100:
            continue
        v = logrets.std() * np.sqrt(BARS_PER_YEAR)
        if v > 0:
            eligible[p] = v

    if not eligible:
        return {p: 0.0 for p in pairs}

    inv_vols = {p: 1.0 / v for p, v in eligible.items()}
    total = sum(inv_vols.values())
    return {p: (inv_vols.get(p, 0.0) / total) if p in eligible else 0.0 for p in pairs}


# =============================================================================
# S13 — BTC-Alpha Long Only (Weight Mode, Monthly)
# =============================================================================

def wt_13_btc_alpha(data, indicators, t, state):
    """
    S13: 'BTC-Alpha Long Only'
    Weight-mode. Each non-BTC asset weighted by its rolling 60d alpha vs BTC
    (OLS residual return). Positive alpha only; BTC itself gets fixed 0.2 allocation.
    Monthly rebalance.

    Avoids v2 failures:
      - Alpha vs BTC is a genuine signal (outperformance is investable).
      - Monthly rebalance = low turnover.
      - Positive-alpha-only filter prevents holding underperformers.
    """
    if t % 720 != 0 or t < 1440:
        return None

    pairs = list(data.keys())
    WINDOW = 1440  # 60d

    btc_ret = None
    if "BTCUSDC" in data:
        btc_close = data["BTCUSDC"]["close"].iloc[t - WINDOW: t]
        btc_ret = np.log(btc_close / btc_close.shift(1)).dropna().values

    alphas = {}
    for p in pairs:
        if p == "BTCUSDC":
            continue
        close_slice = data[p]["close"].iloc[t - WINDOW: t]
        asset_ret = np.log(close_slice / close_slice.shift(1)).dropna().values
        if btc_ret is None or len(asset_ret) < 100 or len(btc_ret) < 100:
            continue
        n = min(len(asset_ret), len(btc_ret))
        x = btc_ret[-n:]
        y = asset_ret[-n:]
        # OLS: y = alpha + beta * x
        beta = np.cov(y, x)[0, 1] / max(np.var(x), 1e-12)
        alpha = np.mean(y) - beta * np.mean(x)
        alpha_ann = alpha * BARS_PER_YEAR  # annualized
        if alpha_ann > 0:
            alphas[p] = alpha_ann

    if not alphas:
        # All flat, give BTC full weight
        return {p: (1.0 if p == "BTCUSDC" else 0.0) for p in pairs}

    total_alpha = sum(alphas.values())
    weights = {}
    btc_weight = 0.20
    remaining = 1.0 - btc_weight
    for p in pairs:
        if p == "BTCUSDC":
            weights[p] = btc_weight
        elif p in alphas:
            weights[p] = (alphas[p] / total_alpha) * remaining
        else:
            weights[p] = 0.0
    return weights


# =============================================================================
# S14 — Triple Screen Trend (Discrete, Multi-Timeframe)
# =============================================================================

def sig_14_triple_screen(data, indicators, t, state, open_legs):
    """
    S14: 'Triple Screen Trend' (Elder-style)
    All 3 must align for entry:
      1. Weekly trend: EMA50 > EMA200 (bull market screen)
      2. Momentum: MACD histogram positive
      3. Hourly entry: RSI < 45 (pullback in uptrend)
    Exit: EMA50 < EMA200 (trend reversal) OR RSI > 75.
    Minimum 48h hold.

    Avoids v2 failures:
      - Three independent filters dramatically reduce false entries.
      - EMA50 > EMA200 is a robust long-term trend gate.
      - RSI < 45 buys dips, preventing chase-tops entries.
    """
    entries, exits = {}, {}
    if t < 200:
        return {"entries": entries, "exits": exits}

    for p in list(data.keys()):
        e50 = _safe(indicators, p, "ema50", t)
        e200 = _safe(indicators, p, "ema200", t)
        macd = _safe(indicators, p, "macd_hist", t)
        rsi = _safe(indicators, p, "rsi14", t)
        if any(np.isnan(v) for v in [e50, e200, macd, rsi]):
            continue

        bull_trend = e50 > e200
        macd_pos = macd > 0
        rsi_pullback = rsi < 45

        if p in open_legs:
            if _min_hold(state, p, t, 48):
                if (not bull_trend) or rsi > 75:
                    exits[p] = True
        else:
            if bull_trend and macd_pos and rsi_pullback:
                entries[p] = {"action": "enter_long", "risk_scale": 1.0}
                _record_entry(state, p, t)

    return {"entries": entries, "exits": exits}


# =============================================================================
# S15 — Accumulation/Distribution Regime (Discrete, Simple)
# =============================================================================

def sig_15_accum_distrib(data, indicators, t, state, open_legs):
    """
    S15: 'Accumulation/Distribution Regime'
    Entry: (close - low) / (high - low) > 0.70 (buyers dominate the bar)
           AND ema20 > ema50 (short-term trend up).
    Exit: (close - low) / (high - low) < 0.30 (sellers dominate) OR ema20 < ema50.
    Minimum 24h hold. Daily evaluation only.

    Avoids v2 failures:
      - Bar-anatomy signal is interpretable; not a black-box oscillator.
      - ema20 > ema50 trend gate prevents buying into downtrends.
      - Daily eval + 24h hold reduces churn dramatically vs hourly check.
    """
    entries, exits = {}, {}
    if t < 50 or t % 24 != 0:
        return {"entries": entries, "exits": exits}

    for p in list(data.keys()):
        high = _safe(indicators, p, "high", t)
        low = _safe(indicators, p, "low", t)
        close = _safe(indicators, p, "close", t)
        e20 = _safe(indicators, p, "ema20", t)
        e50 = _safe(indicators, p, "ema50", t)
        if any(np.isnan(v) for v in [high, low, close, e20, e50]):
            continue
        rng = high - low
        if rng <= 0:
            continue
        buy_pressure = (close - low) / rng

        if p in open_legs:
            if _min_hold(state, p, t, 24) and (buy_pressure < 0.30 or e20 < e50):
                exits[p] = True
        else:
            if buy_pressure > 0.70 and e20 > e50:
                entries[p] = {"action": "enter_long", "risk_scale": 1.0}
                _record_entry(state, p, t)

    return {"entries": entries, "exits": exits}


# =============================================================================
# S16 — Weekly Rotation with Momentum (Weight Mode)
# =============================================================================

def wt_16_weekly_rotation_momentum(data, indicators, t, state):
    """
    S16: 'Weekly Rotation with Momentum and Carry'
    Weight-mode. Rank assets weekly by (mom_72h * 0.5 + mom_30d * 0.5).
    Top-2 get 40% each, 3rd gets 20%. Bottom assets get 0%.
    Rebalance every 168 bars.

    Avoids v2 failures:
      - 72h + 30d composite avoids pure short-term noise.
      - Hard weight caps (0.4/0.4/0.2) prevent concentration risk.
      - Weekly rebalance limits turnover to ~4x/month total.
    """
    if t % 168 != 0 or t < 720:
        return None

    pairs = list(data.keys())
    scores = {}
    for p in pairs:
        m72 = _safe(indicators, p, "mom_72h", t)
        m30 = _safe(indicators, p, "mom_30d", t)
        if np.isnan(m72) or np.isnan(m30):
            continue
        scores[p] = 0.5 * m72 + 0.5 * m30

    if not scores:
        return None

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    weights_map = {}
    alloc = [0.40, 0.40, 0.20]
    for i, (p, s) in enumerate(ranked):
        if i < len(alloc) and s > 0:
            weights_map[p] = alloc[i]
        else:
            weights_map[p] = 0.0

    return {p: weights_map.get(p, 0.0) for p in pairs}


# =============================================================================
# S17 — Regime-Gated Mean Reversion (Discrete, Very Selective)
# =============================================================================

def sig_17_regime_gated_mean_revert(data, indicators, t, state, open_legs):
    """
    S17: 'Regime-Gated Mean Reversion'
    Entry: |zscore50| > 2.0 AND ADX < 20 (no trend) AND bb_width_norm < 0.30 (range-bound).
    Exit: zscore50 crosses back through 0.
    Minimum 48h hold. Only fade in genuine range-bound conditions.

    Avoids v2 failures:
      - ADX < 20 gate strictly prevents fading strong trends.
      - bb_width_norm < 0.30 confirms range environment.
      - zscore50 > 2.0 is selective — far fewer signals than > 1.5.
      - Exit at zscore=0 (mean) not at reversal signal — avoids overtrading.
    """
    entries, exits = {}, {}
    if t < 50:
        return {"entries": entries, "exits": exits}

    for p in list(data.keys()):
        z = _safe(indicators, p, "zscore50", t)
        adx = _safe(indicators, p, "adx14", t)
        bwn = _safe(indicators, p, "bb_width_norm", t)
        if any(np.isnan(v) for v in [z, adx, bwn]):
            continue

        in_range = (adx < 20) and (bwn < 0.30)

        if p in open_legs:
            direction = open_legs[p].direction if hasattr(open_legs[p], "direction") else 0
            # Exit when zscore reverts toward 0
            if _min_hold(state, p, t, 48):
                prev_entry_z = state.get(f"z_entry_{p}", 0.0)
                if prev_entry_z > 0 and z <= 0:
                    exits[p] = True
                elif prev_entry_z < 0 and z >= 0:
                    exits[p] = True
        else:
            if in_range and abs(z) > 2.0:
                action = "enter_short" if z > 2.0 else "enter_long"
                entries[p] = {"action": action, "risk_scale": 1.0}
                _record_entry(state, p, t)
                state[f"z_entry_{p}"] = z

    return {"entries": entries, "exits": exits}


# =============================================================================
# S18 — Monthly Cointegration Spread (Stat-Arb, Very Selective)
# =============================================================================

def sig_18_monthly_cointegration(data, indicators, t, state, open_legs):
    """
    S18: 'Monthly Cointegration Spread'
    Once per month (720 bars), run ADF test on all pair combinations.
    Trade ONLY the single pair with p < 0.02 (very strict). One pair at a time.
    Exit after 336 bars (14 days) OR when z-score of spread reaches 0.
    No re-entry until next monthly selection.

    Avoids v2 failures:
      - p < 0.02 ADF threshold is extremely strict — very few entries.
      - One pair at a time, monthly cap: at most 6 entries per year per relationship.
      - 336-bar max hold prevents zombie positions.
    """
    entries, exits = {}, {}
    pairs = list(data.keys())

    # -- Exits for active spread leg --
    for p in list(open_legs.keys()):
        entry_bar = state.get(f"entry_{p}", 0)
        spread_mean = state.get(f"spread_mean_{p}", 0.0)
        spread_std = state.get(f"spread_std_{p}", 1.0)
        beta_pair = state.get(f"beta_{p}", None)

        # Time-based exit after 14 days (336h)
        if t - entry_bar >= 336:
            exits[p] = True
            # Also exit the hedge leg
            hedge = state.get(f"hedge_{p}")
            if hedge and hedge in open_legs:
                exits[hedge] = True
            continue

        # Spread z-score exit at 0
        if beta_pair is not None:
            hedge = state.get(f"hedge_{p}")
            if hedge and hedge in data:
                c_p = data[p]["close"].iat[t]
                c_h = data[hedge]["close"].iat[t]
                spread = c_p - beta_pair * c_h
                z = (spread - spread_mean) / max(spread_std, 1e-8)
                entry_z = state.get(f"z_entry_{p}", 0.0)
                if (entry_z > 0 and z <= 0) or (entry_z < 0 and z >= 0):
                    exits[p] = True
                    if hedge in open_legs:
                        exits[hedge] = True

    # -- Monthly selection --
    if t % 720 != 0 or t < 1440:
        return {"entries": entries, "exits": exits}

    # Skip if any spread position is active
    if open_legs:
        return {"entries": entries, "exits": exits}

    WINDOW = 1440  # 60d
    best_p_val = 1.0
    best_pair = None
    best_hedge = None
    best_beta = None
    best_z = None
    best_spread_mean = None
    best_spread_std = None

    for i, p1 in enumerate(pairs):
        for p2 in pairs[i + 1:]:
            try:
                y1 = data[p1]["close"].iloc[t - WINDOW: t].values
                y2 = data[p2]["close"].iloc[t - WINDOW: t].values
                if len(y1) < 200 or len(y2) < 200:
                    continue
                # OLS beta: y1 = alpha + beta * y2
                beta = np.cov(y1, y2)[0, 1] / max(np.var(y2), 1e-12)
                spread = y1 - beta * y2
                adf_res = adfuller(spread, maxlag=10, autolag="AIC")
                p_val = adf_res[1]
                if p_val < best_p_val:
                    best_p_val = p_val
                    best_pair = p1
                    best_hedge = p2
                    best_beta = beta
                    best_spread_mean = float(np.mean(spread))
                    best_spread_std = float(np.std(spread))
                    cur_z = (spread[-1] - best_spread_mean) / max(best_spread_std, 1e-8)
                    best_z = cur_z
            except Exception:
                continue

    if best_p_val < 0.02 and best_pair is not None and abs(best_z) > 1.5:
        # Short the high side, long the low side
        action_p = "enter_short" if best_z > 0 else "enter_long"
        action_h = "enter_long" if best_z > 0 else "enter_short"
        entries[best_pair] = {"action": action_p, "risk_scale": 0.5}
        entries[best_hedge] = {"action": action_h, "risk_scale": 0.5}
        _record_entry(state, best_pair, t)
        _record_entry(state, best_hedge, t)
        state[f"beta_{best_pair}"] = best_beta
        state[f"hedge_{best_pair}"] = best_hedge
        state[f"hedge_{best_hedge}"] = best_pair
        state[f"spread_mean_{best_pair}"] = best_spread_mean
        state[f"spread_std_{best_pair}"] = best_spread_std
        state[f"z_entry_{best_pair}"] = best_z
        state[f"z_entry_{best_hedge}"] = -best_z

    return {"entries": entries, "exits": exits}


# =============================================================================
# S19 — BTC Lead Signal for Alts (Discrete, Event-Driven)
# =============================================================================

def sig_19_btc_lead_signal(data, indicators, t, state, open_legs):
    """
    S19: 'Inter-Market BTC Lead Signal'
    If BTC breaks above its 24h high by > 0.5% AND ADX(BTC) > 25,
    enter the top-1 alt by 72h momentum (not BTC itself).
    Exit when BTC drops below its 24h open.
    Minimum 24h hold. At most 1 concurrent.

    Avoids v2 failures:
      - BTC leadership is a genuine cross-market signal (not noise).
      - Only 1 concurrent leg = very few entries.
      - ADX > 25 gate prevents signal on low-vol drift.
      - 72h momentum picks the alt with real underlying strength.
    """
    entries, exits = {}, {}
    if t < 25 or "BTCUSDC" not in data:
        return {"entries": entries, "exits": exits}

    btc_close = data["BTCUSDC"]["close"].iat[t]
    btc_open_24h = data["BTCUSDC"]["open"].iat[t - 24] if t >= 24 else np.nan
    btc_high_24h = data["BTCUSDC"]["high"].iloc[t - 24: t].max() if t >= 24 else np.nan
    btc_adx = _safe(indicators, "BTCUSDC", "adx14", t)

    # Handle exits
    alts = [p for p in data.keys() if p != "BTCUSDC"]
    for p in list(open_legs.keys()):
        if _min_hold(state, p, t, 24) and not np.isnan(btc_open_24h):
            if btc_close < btc_open_24h:
                exits[p] = True

    # Only one concurrent alt leg
    if len(open_legs) >= 1:
        return {"entries": entries, "exits": exits}

    if np.isnan(btc_close) or np.isnan(btc_high_24h) or np.isnan(btc_adx):
        return {"entries": entries, "exits": exits}

    btc_breakout = (btc_close > btc_high_24h * 1.005) and (btc_adx > 25)
    if not btc_breakout:
        return {"entries": entries, "exits": exits}

    # Pick top-1 alt by 72h momentum
    alt_moms = {}
    for p in alts:
        m = _safe(indicators, p, "mom_72h", t)
        if not np.isnan(m):
            alt_moms[p] = m

    if not alt_moms:
        return {"entries": entries, "exits": exits}

    top_alt = max(alt_moms.items(), key=lambda kv: kv[1])
    if top_alt[1] > 0:
        entries[top_alt[0]] = {"action": "enter_long", "risk_scale": 1.0}
        _record_entry(state, top_alt[0], t)

    return {"entries": entries, "exits": exits}


# =============================================================================
# S20 — Price Mean Reversion with Trend Abort (Discrete)
# =============================================================================

def sig_20_mean_revert_trend_abort(data, indicators, t, state, open_legs):
    """
    S20: 'Price Mean Reversion with Trend Abort'
    Entry: |zscore50| > 2.5 (very extreme).
    Exit: zscore50 reverts to 0 OR EMA20 crosses EMA50 against position.
    Max hold 168 bars (7 days). No entry if ADX > 25 (trending — abort).

    Avoids v2 failures:
      - zscore > 2.5 threshold is very selective (fewer signals than > 2.0).
      - ADX > 25 abort prevents fading strong trends entirely.
      - EMA cross abort is the emergency exit on regime change.
      - 168-bar max hold prevents zombie positions.
    """
    entries, exits = {}, {}
    if t < 50:
        return {"entries": entries, "exits": exits}

    for p in list(data.keys()):
        z = _safe(indicators, p, "zscore50", t)
        e20 = _safe(indicators, p, "ema20", t)
        e50 = _safe(indicators, p, "ema50", t)
        adx = _safe(indicators, p, "adx14", t)
        if any(np.isnan(v) for v in [z, e20, e50, adx]):
            continue

        if p in open_legs:
            entry_bar = state.get(f"entry_{p}", 0)
            entry_z = state.get(f"z_entry_{p}", 0.0)
            age = t - entry_bar

            # Time-based max hold exit
            if age >= 168:
                exits[p] = True
                continue

            # Trend-abort: EMA cross against position direction
            ema_cross_against = False
            if entry_z > 0:  # was short (fading high z)
                ema_cross_against = e20 > e50  # trend now up → abort short
            elif entry_z < 0:  # was long (fading low z)
                ema_cross_against = e20 < e50  # trend now down → abort long

            # Revert-to-mean exit
            z_reverted = (entry_z > 0 and z <= 0) or (entry_z < 0 and z >= 0)

            if ema_cross_against or z_reverted:
                exits[p] = True
        else:
            # Entry: extreme z AND no strong trend
            if abs(z) > 2.5 and adx < 25:
                action = "enter_short" if z > 2.5 else "enter_long"
                entries[p] = {"action": action, "risk_scale": 1.0}
                _record_entry(state, p, t)
                state[f"z_entry_{p}"] = z

    return {"entries": entries, "exits": exits}


# =============================================================================
# Registry
# =============================================================================

def build_strategies() -> list:
    """Return list of all 20 StrategyConfig objects for the v3 suite."""
    return [
        StrategyConfig(
            id="MP-V3-S01",
            name="90d High Momentum Breakout",
            archetype="trend_following",
            mode="discrete",
            signal_fn=sig_01_90d_high_breakout,
            max_concurrent_legs=3,
            risk_per_trade=0.01,
            portfolio_heat_cap=0.05,
            atr_stop_mult=2.5,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S02",
            name="Multi-Period Momentum Composite",
            archetype="momentum_rotation",
            mode="discrete",
            signal_fn=sig_02_composite_momentum,
            max_concurrent_legs=2,
            risk_per_trade=0.015,
            portfolio_heat_cap=0.05,
            atr_stop_mult=2.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S03",
            name="EMA Slope Acceleration",
            archetype="trend_following",
            mode="discrete",
            signal_fn=sig_03_ema_slope_accel,
            max_concurrent_legs=4,
            risk_per_trade=0.01,
            portfolio_heat_cap=0.05,
            atr_stop_mult=2.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S04",
            name="Trend Pullback Entry",
            archetype="trend_following",
            mode="discrete",
            signal_fn=sig_04_trend_pullback,
            max_concurrent_legs=3,
            risk_per_trade=0.012,
            portfolio_heat_cap=0.05,
            atr_stop_mult=2.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S05",
            name="Absolute Momentum 6-Month Barrier",
            archetype="abs_momentum",
            mode="discrete",
            signal_fn=sig_05_abs_momentum_6m,
            max_concurrent_legs=5,
            risk_per_trade=0.01,
            portfolio_heat_cap=0.05,
            atr_stop_mult=3.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S06",
            name="Volatility Contraction Breakout",
            archetype="vol_breakout",
            mode="discrete",
            signal_fn=sig_06_vix_squeeze_breakout,
            max_concurrent_legs=2,
            risk_per_trade=0.015,
            portfolio_heat_cap=0.04,
            atr_stop_mult=2.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S07",
            name="ATR Expansion Trend",
            archetype="vol_breakout",
            mode="discrete",
            signal_fn=sig_07_atr_expansion_trend,
            max_concurrent_legs=3,
            risk_per_trade=0.01,
            portfolio_heat_cap=0.05,
            atr_stop_mult=2.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S08",
            name="Low-Vol Momentum Carry",
            archetype="regime_momentum",
            mode="discrete",
            signal_fn=sig_08_lowvol_momentum_carry,
            max_concurrent_legs=3,
            risk_per_trade=0.01,
            portfolio_heat_cap=0.05,
            atr_stop_mult=2.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S09",
            name="Vol Mean Reversion Short",
            archetype="vol_regime",
            mode="discrete",
            signal_fn=sig_09_vol_mean_reversion_short,
            max_concurrent_legs=1,
            risk_per_trade=0.008,
            portfolio_heat_cap=0.03,
            atr_stop_mult=2.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S10",
            name="Pure Equal Weight Momentum",
            archetype="weight_rotation",
            mode="weight",
            weight_fn=wt_10_equal_weight_momentum,
            max_concurrent_legs=5,
            risk_per_trade=0.01,
            portfolio_heat_cap=0.05,
            atr_stop_mult=2.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S11",
            name="Min Variance Portfolio",
            archetype="risk_parity",
            mode="weight",
            weight_fn=wt_11_min_variance,
            max_concurrent_legs=5,
            risk_per_trade=0.01,
            portfolio_heat_cap=0.05,
            atr_stop_mult=2.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S12",
            name="Risk Parity with Momentum Filter",
            archetype="risk_parity",
            mode="weight",
            weight_fn=wt_12_risk_parity_momentum,
            max_concurrent_legs=5,
            risk_per_trade=0.01,
            portfolio_heat_cap=0.05,
            atr_stop_mult=2.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S13",
            name="BTC-Alpha Long Only",
            archetype="factor_weight",
            mode="weight",
            weight_fn=wt_13_btc_alpha,
            max_concurrent_legs=5,
            risk_per_trade=0.01,
            portfolio_heat_cap=0.05,
            atr_stop_mult=2.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S14",
            name="Triple Screen Trend",
            archetype="multi_timeframe",
            mode="discrete",
            signal_fn=sig_14_triple_screen,
            max_concurrent_legs=3,
            risk_per_trade=0.012,
            portfolio_heat_cap=0.05,
            atr_stop_mult=2.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S15",
            name="Accumulation Distribution Regime",
            archetype="order_flow",
            mode="discrete",
            signal_fn=sig_15_accum_distrib,
            max_concurrent_legs=3,
            risk_per_trade=0.01,
            portfolio_heat_cap=0.05,
            atr_stop_mult=2.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S16",
            name="Weekly Rotation Momentum Carry",
            archetype="weight_rotation",
            mode="weight",
            weight_fn=wt_16_weekly_rotation_momentum,
            max_concurrent_legs=5,
            risk_per_trade=0.01,
            portfolio_heat_cap=0.05,
            atr_stop_mult=2.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S17",
            name="Regime-Gated Mean Reversion",
            archetype="mean_reversion",
            mode="discrete",
            signal_fn=sig_17_regime_gated_mean_revert,
            max_concurrent_legs=2,
            risk_per_trade=0.008,
            portfolio_heat_cap=0.04,
            atr_stop_mult=1.5,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S18",
            name="Monthly Cointegration Spread",
            archetype="stat_arb",
            mode="discrete",
            signal_fn=sig_18_monthly_cointegration,
            max_concurrent_legs=2,
            risk_per_trade=0.008,
            portfolio_heat_cap=0.04,
            atr_stop_mult=2.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S19",
            name="BTC Lead Signal for Alts",
            archetype="cross_market",
            mode="discrete",
            signal_fn=sig_19_btc_lead_signal,
            max_concurrent_legs=1,
            risk_per_trade=0.015,
            portfolio_heat_cap=0.03,
            atr_stop_mult=2.0,
            max_gross_leverage=1.0,
        ),
        StrategyConfig(
            id="MP-V3-S20",
            name="Price Mean Reversion Trend Abort",
            archetype="mean_reversion",
            mode="discrete",
            signal_fn=sig_20_mean_revert_trend_abort,
            max_concurrent_legs=2,
            risk_per_trade=0.008,
            portfolio_heat_cap=0.04,
            atr_stop_mult=1.5,
            max_gross_leverage=1.0,
        ),
    ]
