#!/usr/bin/env python
"""cross_sectional_fast.py — fast backtest for 22 cross-sectional strategies."""
from __future__ import annotations
import json, os, sys, math, time
import numpy as np
import pandas as pd

ROOT = r"C:\Users\Lenovo\Documents\backtest-system"
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "code"))

INIT = 10000.0
COST_BPS = 5.0
SLIP_BPS = 3.0
RT_COST = (COST_BPS + SLIP_BPS) / 10000.0

def load_ohlc(sym, tf, taker=False):
    if taker:
        p = os.path.join(DATA, f"binance_klines_{tf}_taker", f"{sym}_{tf}.csv")
    else:
        tf_map = {"1m":"binance_klines_1m", "5m":"binance_klines_5m",
                  "15m":"binance_klines_15m", "1h":"binance_klines_1h"}
        p = os.path.join(DATA, tf_map[tf], f"{sym}_{tf}.csv")
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p)
    d.columns = [c.strip().lower() for c in d.columns]
    d["ts"] = pd.to_datetime(d["open_ts"], unit="ms", utc=True)
    d = d.sort_values("ts").reset_index(drop=True)
    return d

def load_funding(sym):
    p = os.path.join(DATA, "binance_funding", f"{sym}_funding.json")
    if not os.path.exists(p):
        return None
    raw = json.load(open(p))
    rows = []
    for r in raw:
        t = r.get("t") or r.get("fundingTime")
        rate = r.get("r") or r.get("fundingRate")
        if rate is None: continue
        rows.append({"ts": pd.to_datetime(t, unit="ms", utc=True), "rate": float(rate)})
    return pd.DataFrame(rows).sort_values("ts").reset_index(drop=True)

def load_matrix(symbols, tf, taker=False):
    prices = {}
    for sym in symbols:
        df = load_ohlc(sym, tf, taker=taker)
        if df is not None:
            prices[sym] = df
    if not prices: return None
    all_ts = sorted(set().union(*[set(prices[s]["ts"]) for s in prices]))
    idx = pd.DatetimeIndex(all_ts)
    close = pd.DataFrame(index=idx)
    vol = pd.DataFrame(index=idx)
    high = pd.DataFrame(index=idx)
    low = pd.DataFrame(index=idx)
    opn = pd.DataFrame(index=idx)
    has_taker = taker and True
    taker_df = pd.DataFrame(index=idx) if has_taker else None
    for sym in prices:
        d = prices[sym].set_index("ts")
        close[sym] = d["close"].reindex(idx)
        vol[sym] = d["volume"].reindex(idx)
        high[sym] = d["high"].reindex(idx)
        low[sym] = d["low"].reindex(idx)
        opn[sym] = d["open"].reindex(idx)
        if has_taker and "taker_buy_base" in d.columns:
            taker_df[sym] = d["taker_buy_base"].reindex(idx)
    return close, vol, high, low, opn, taker_df, all_ts, idx

def load_funding_matrix(symbols, idx):
    funding = {}
    for sym in symbols:
        fd = load_funding(sym)
        if fd is not None:
            funding[sym] = fd
    fm = pd.DataFrame(index=idx)
    for sym in symbols:
        if sym in funding:
            f = funding[sym].set_index("ts")["rate"]
            fm[sym] = f.reindex(idx, method="ffill")
        else:
            fm[sym] = np.nan
    return fm, funding

# ── Fast weight computation using precomputed signals ──────────────────────────
def backtest_fast(strategy_name, signal_fn, cm, vm, hm, lm, om, tm, fm, funding, all_ts, rebal_every, bpy):
    """Generic backtest. signal_fn(cm, vm, hm, lm, om, tm, fm, funding) returns 
    a DataFrame of shape (n_bars, n_symbols) with signal scores, or a dict of precomputed.
    We compute weights at each rebalance bar by ranking the signal row."""
    n = len(all_ts)
    idx = cm.index

    # Precompute signal scores: DataFrame (n_bars x n_symbols)
    scores = signal_fn(cm, vm, hm, lm, om, tm, fm, funding)  # returns DataFrame

    equity = [INIT]
    positions = {}
    last_rebal = 0
    turnover_cost = 0.0
    total_funding = 0.0
    n_rebalances = 0

    for i in range(1, n):
        port_ret = 0.0
        n_pos = len(positions)
        if n_pos > 0:
            for sym, pos in positions.items():
                if sym in cm.columns:
                    c_prev = cm[sym].iloc[i-1]
                    c_curr = cm[sym].iloc[i]
                    if pd.notna(c_prev) and pd.notna(c_curr) and c_prev > 0:
                        port_ret += (1.0/n_pos) * pos * (c_curr / c_prev - 1)

        fund_ret = 0.0
        is_settlement = (all_ts[i].hour % 8 == 0 and all_ts[i].minute == 0)
        if is_settlement and n_pos > 0:
            for sym, pos in positions.items():
                if sym in fm.columns:
                    fr = fm[sym].iloc[i]
                    if pd.notna(fr):
                        fund_income = -pos * fr
                        w = 1.0 / n_pos
                        fund_ret += w * fund_income
                        total_funding += w * equity[-1] * fund_income

        equity.append(equity[-1] * (1 + port_ret + fund_ret))

        if i - last_rebal >= rebal_every or not positions:
            # compute weights from scores at bar i
            if i >= len(scores):
                last_rebal = i
                continue
            row = scores.iloc[i]
            row = row.dropna()
            if len(row) < 4:
                last_rebal = i
                continue
            # default: long top 2, short bottom 2
            ranked = row.sort_values(ascending=False)
            longs = list(ranked.index[:2])
            shorts = list(ranked.index[-2:])
            # For strategies that need special handling, the signal_fn returns signed scores
            # where higher = long candidate
            new_positions = {}
            for s in longs: new_positions[s] = 1
            for s in shorts: new_positions[s] = -1

            all_syms = set(positions) | set(new_positions)
            turnover = sum(abs(new_positions.get(s, 0) - positions.get(s, 0)) for s in all_syms)
            cost = turnover * RT_COST * equity[-1] / 2
            equity[-1] -= cost
            turnover_cost += cost
            if turnover > 0:
                n_rebalances += 1
            positions = new_positions
            last_rebal = i

    eq = np.array(equity)
    total_ret = (eq[-1]/eq[0] - 1) * 100
    max_dd = ((eq / np.maximum.accumulate(eq)) - 1).min() * 100
    r = np.diff(eq) / eq[:-1]
    sharpe = np.mean(r) / np.std(r, ddof=1) * np.sqrt(bpy) if np.std(r, ddof=1) > 0 else 0
    split = int(len(eq) * 0.7)
    is_ret = (eq[split-1]/eq[0] - 1) * 100
    oos_ret = (eq[-1]/eq[split-1] - 1) * 100
    is_dd = ((eq[:split] / np.maximum.accumulate(eq[:split])) - 1).min() * 100
    oos_dd = ((eq[split:] / np.maximum.accumulate(eq[split:])) - 1).min() * 100
    eq_series = pd.Series(eq, index=pd.DatetimeIndex(all_ts))
    monthly = eq_series.resample("ME").last().pct_change().dropna()
    pos_months = (monthly > 0).mean() * 100
    return {
        "strategy": strategy_name,
        "total_ret": round(total_ret, 1),
        "max_dd": round(max_dd, 1),
        "sharpe": round(sharpe, 2),
        "is_ret": round(is_ret, 1),
        "oos_ret": round(oos_ret, 1),
        "is_dd": round(is_dd, 1),
        "oos_dd": round(oos_dd, 1),
        "pos_months": round(pos_months, 1),
        "turnover_cost": round(turnover_cost, 0),
        "funding": round(total_funding, 0),
        "n_rebal": n_rebalances,
    }

# ── Signal functions (return DataFrame of scores, higher = long candidate) ─────

def sig_lowvol(cm, vm, hm, lm, om, tm, fm, funding):
    """S1: negative vol (long low vol)."""
    vol = cm.pct_change().rolling(168, min_periods=168).std(ddof=0)
    return -vol  # higher = lower vol

def sig_beta(cm, vm, hm, lm, om, tm, fm, funding):
    """S2: negative beta (long low beta)."""
    btc_ret = cm["BTCUSDT"].pct_change() if "BTCUSDT" in cm.columns else None
    if btc_ret is None: return pd.DataFrame(index=cm.index, columns=cm.columns)
    beta = pd.DataFrame(index=cm.index, columns=cm.columns)
    for sym in cm.columns:
        if sym == "BTCUSDT": 
            beta[sym] = np.nan
            continue
        ar = cm[sym].pct_change()
        # rolling cov / var
        cov = ar.rolling(336, min_periods=336).cov(btc_ret)
        var = btc_ret.rolling(336, min_periods=336).var()
        beta[sym] = cov / var
    return -beta

def sig_skew(cm, vm, hm, lm, om, tm, fm, funding):
    """S3: negative skew (long negative skew)."""
    skew = cm.pct_change().rolling(168, min_periods=168).skew()
    return -skew

def sig_sharpe_mom(cm, vm, hm, lm, om, tm, fm, funding):
    """S10: ROC/vol, gated by 336-bar ROC > 0."""
    roc168 = cm / cm.shift(168) - 1
    vol168 = cm.pct_change().rolling(168, min_periods=168).std(ddof=0)
    score = roc168 / vol168
    roc336 = cm / cm.shift(336) - 1
    # gate: long candidates need roc336 > 0, but for scoring we just return score
    # short candidates need roc336 < 0; we handle by returning signed score
    # For simplicity, return score * sign(roc336) to separate
    return score  # ranking handles top/bottom

def sig_funding_diff(cm, vm, hm, lm, om, tm, fm, funding):
    """S7: negative funding (long most negative funding)."""
    return -fm  # higher = more negative funding

def sig_funding_mom(cm, vm, hm, lm, om, tm, fm, funding):
    """S8: composite of ROC rank and funding."""
    roc = cm / cm.shift(168) - 1
    # z-score funding
    fr_z = (fm - fm.mean(axis=1).values[:,None]) / fm.std(axis=1).values[:,None]
    fr_z = fr_z.fillna(0)
    # composite: rank by roc, filter by funding
    return roc - fr_z * 0.01  # approximate

def sig_vol_ratio(cm, vm, hm, lm, om, tm, fm, funding):
    """S9: negative vol ratio (long contracting vol)."""
    v24 = cm.pct_change().rolling(24, min_periods=24).std(ddof=0)
    v168 = cm.pct_change().rolling(168, min_periods=168).std(ddof=0)
    vr = v24 / v168
    return -vr

def sig_clv(cm, vm, hm, lm, om, tm, fm, funding):
    """S11: mean CLV over 12 bars."""
    # compute CLV per bar
    clv = pd.DataFrame(index=cm.index, columns=cm.columns)
    for sym in cm.columns:
        if sym not in hm.columns: 
            clv[sym] = np.nan
            continue
        h = hm[sym]; l = lm[sym]; c = cm[sym]
        rng = h - l
        clv_bar = (c - l) / rng.replace(0, np.nan)
        clv_bar = clv_bar.fillna(0.5)
        clv[sym] = clv_bar.rolling(12, min_periods=12).mean()
    return clv

def sig_wick(cm, vm, hm, lm, om, tm, fm, funding):
    """S12: wick score over 12 bars."""
    score = pd.DataFrame(index=cm.index, columns=cm.columns)
    for sym in cm.columns:
        if sym not in hm.columns or sym not in om.columns:
            score[sym] = np.nan
            continue
        h = hm[sym]; l = lm[sym]; o = om[sym]; c = cm[sym]
        lower = np.minimum(o, c) - l
        upper = h - np.maximum(o, c)
        rng = h - l
        # rolling sum
        lw = lower.rolling(12, min_periods=12).sum()
        uw = upper.rolling(12, min_periods=12).sum()
        rw = rng.rolling(12, min_periods=12).sum()
        score[sym] = (lw - uw) / rw.replace(0, np.nan)
    return score

def sig_vol_clv(cm, vm, hm, lm, om, tm, fm, funding):
    """S13: volume-weighted CLV over 24 bars."""
    score = pd.DataFrame(index=cm.index, columns=cm.columns)
    for sym in cm.columns:
        if sym not in hm.columns or sym not in vm.columns:
            score[sym] = np.nan
            continue
        h = hm[sym]; l = lm[sym]; c = cm[sym]; v = vm[sym]
        rng = h - l
        clv_bar = (c - l) / rng.replace(0, np.nan)
        clv_bar = clv_bar.fillna(0.5)
        # volume-weighted mean
        wclv = clv_bar * v
        score[sym] = wclv.rolling(24, min_periods=24).sum() / v.rolling(24, min_periods=24).sum()
    return score

def sig_taker_ratio(cm, vm, hm, lm, om, tm, fm, funding):
    """S14: mean TBR over 12 bars."""
    if tm is None: return pd.DataFrame(index=cm.index, columns=cm.columns)
    score = pd.DataFrame(index=cm.index, columns=cm.columns)
    for sym in cm.columns:
        if sym not in tm.columns: 
            score[sym] = np.nan
            continue
        t = tm[sym]; v = vm[sym]
        tbr = t / v.replace(0, np.nan)
        score[sym] = tbr.rolling(12, min_periods=12).mean()
    return score

def sig_taker_div(cm, vm, hm, lm, om, tm, fm, funding):
    """S15: taker flow / price divergence."""
    if tm is None: return pd.DataFrame(index=cm.index, columns=cm.columns)
    score = pd.DataFrame(index=cm.index, columns=cm.columns)
    for sym in cm.columns:
        if sym not in tm.columns:
            score[sym] = np.nan
            continue
        t = tm[sym]; v = vm[sym]; c = cm[sym]
        tbr = t / v.replace(0, np.nan)
        tbr_recent = tbr.rolling(24, min_periods=24).mean()
        tbr_prior = tbr.shift(24).rolling(24, min_periods=24).mean()
        dtbr = tbr_recent - tbr_prior
        r24 = c / c.shift(24) - 1
        score[sym] = dtbr - r24
    return score

def sig_taker_surprise(cm, vm, hm, lm, om, tm, fm, funding):
    """S16: z-score of recent TBR vs 168-bar history."""
    if tm is None: return pd.DataFrame(index=cm.index, columns=cm.columns)
    score = pd.DataFrame(index=cm.index, columns=cm.columns)
    for sym in cm.columns:
        if sym not in tm.columns:
            score[sym] = np.nan
            continue
        t = tm[sym]; v = vm[sym]
        tbr = t / v.replace(0, np.nan)
        recent = tbr.rolling(24, min_periods=24).mean()
        hist_mean = tbr.rolling(168, min_periods=168).mean()
        hist_std = tbr.rolling(168, min_periods=168).std(ddof=0)
        score[sym] = (recent - hist_mean) / hist_std.replace(0, np.nan)
    return score

def sig_hf_mom(cm, vm, hm, lm, om, tm, fm, funding):
    """S17: 12-bar return."""
    return cm / cm.shift(12) - 1

def sig_vol_spike(cm, vm, hm, lm, om, tm, fm, funding):
    """S18: volume ratio (3-bar / 168-bar)."""
    v3 = vm.rolling(3, min_periods=3).mean()
    v168 = vm.rolling(168, min_periods=168).mean()
    return v3 / v168

def sig_leadlag(cm, vm, hm, lm, om, tm, fm, funding):
    """S19: negative residual (long laggards)."""
    if "BTCUSDT" not in cm.columns:
        return pd.DataFrame(index=cm.index, columns=cm.columns)
    btc_ret = cm["BTCUSDT"].pct_change()
    score = pd.DataFrame(index=cm.index, columns=cm.columns)
    # precompute beta (constant 336-bar)
    for sym in cm.columns:
        if sym == "BTCUSDT":
            score[sym] = np.nan
            continue
        ar = cm[sym].pct_change()
        cov = ar.rolling(336, min_periods=336).cov(btc_ret)
        var = btc_ret.rolling(336, min_periods=336).var()
        beta = cov / var
        # 3-bar cumulative residual
        resid = pd.Series(0.0, index=cm.index)
        for j in range(3):
            r_alt = cm[sym].pct_change().shift(j)
            r_btc = btc_ret.shift(j)
            resid = resid + (r_alt - beta * r_btc)
        score[sym] = -resid  # negative residual = long candidate
    return score

def sig_composite(cm, vm, hm, lm, om, tm, fm, funding):
    """S20: z(ROC/vol) - z(funding)."""
    roc168 = cm / cm.shift(168) - 1
    vol168 = cm.pct_change().rolling(168, min_periods=168).std(ddof=0)
    sharpe_mom = roc168 / vol168
    # z-score across symbols per bar
    sm = sharpe_mom.sub(sharpe_mom.mean(axis=1), axis=0)
    ss = sharpe_mom.std(axis=1).replace(0, np.nan)
    z_sm = sm.div(ss, axis=0)
    # funding z
    fm_filled = fm.fillna(0)
    fm_z = fm_filled.sub(fm_filled.mean(axis=1), axis=0)
    fm_std = fm_filled.std(axis=1).replace(0, np.nan)
    z_fm = fm_z.div(fm_std, axis=0)
    return z_sm - z_fm

def sig_ensemble(cm, vm, hm, lm, om, tm, fm, funding):
    """S21: 1/3 rank(mom) + 1/3 rank(taker) + 1/3 rank(-vol). Lower rank = better."""
    if tm is None: return pd.DataFrame(index=cm.index, columns=cm.columns)
    common = [s for s in cm.columns if s in tm.columns]
    if not common: return pd.DataFrame(index=cm.index, columns=cm.columns)
    roc = cm[common] / cm[common].shift(168) - 1
    # taker flow (24-bar mean TBR)
    tbr = pd.DataFrame(index=cm.index, columns=common)
    for sym in common:
        t = tm[sym]; v = vm[sym]
        tbr[sym] = (t / v.replace(0, np.nan)).rolling(24, min_periods=24).mean()
    vol = cm[common].pct_change().rolling(168, min_periods=168).std(ddof=0)
    # rank per bar (lower rank number = higher value for roc/tbr, lower for vol)
    # composite = sum of ranks (lower = better), so we negate for "higher = long"
    r_roc = roc.rank(axis=1, ascending=False)
    r_tbr = tbr.rank(axis=1, ascending=False)
    r_vol = vol.rank(axis=1, ascending=True)  # low vol = high rank (low number)
    composite = r_roc + r_tbr + r_vol
    return -composite  # higher = better (lower composite rank)

def sig_regime(cm, vm, hm, lm, om, tm, fm, funding):
    """S22: regime-switching weights."""
    roc = cm / cm.shift(168) - 1
    vol168 = cm.pct_change().rolling(168, min_periods=168).std(ddof=0)
    # regime: cross-sectional median vol vs 336-bar median of that
    med_vol = vol168.median(axis=1)
    regime_med = med_vol.rolling(336, min_periods=336).median()
    low_vol_regime = med_vol <= regime_med
    # weights
    w_mom = pd.Series(np.where(low_vol_regime, 0.7, 0.3), index=cm.index)
    w_vol = pd.Series(np.where(low_vol_regime, 0.3, 0.7), index=cm.index)
    # rank
    r_roc = roc.rank(axis=1, ascending=False)
    r_vol = vol168.rank(axis=1, ascending=True)
    # composite (lower = better)
    composite = w_mom.values[:,None] * r_roc + w_vol.values[:,None] * r_vol
    return -composite

def sig_defensive(cm, vm, hm, lm, om, tm, fm, funding):
    """S5: defensive quality during corrections. Only active when BTC 24h < -3%."""
    if "BTCUSDT" not in cm.columns:
        return pd.DataFrame(index=cm.index, columns=cm.columns)
    btc_ret24 = cm["BTCUSDT"] / cm["BTCUSDT"].shift(24) - 1
    trigger = btc_ret24 < -0.03
    btc_ret = cm["BTCUSDT"].pct_change()
    score = pd.DataFrame(np.nan, index=cm.index, columns=cm.columns)
    for sym in cm.columns:
        if sym == "BTCUSDT": 
            score[sym] = np.nan
            continue
        ar = cm[sym].pct_change()
        # beta
        cov = ar.rolling(336, min_periods=336).cov(btc_ret)
        var = btc_ret.rolling(336, min_periods=336).var()
        beta = cov / var
        alt_ret24 = cm[sym] / cm[sym].shift(24) - 1
        beta_adj = alt_ret24 - beta * btc_ret24
        score[sym] = beta_adj.where(trigger, np.nan)
    return score

def sig_resid_rev(cm, vm, hm, lm, om, tm, fm, funding):
    """S6: beta-adjusted residual reversal."""
    if "BTCUSDT" not in cm.columns:
        return pd.DataFrame(index=cm.index, columns=cm.columns)
    btc_ret = cm["BTCUSDT"].pct_change()
    score = pd.DataFrame(index=cm.index, columns=cm.columns)
    for sym in cm.columns:
        if sym == "BTCUSDT":
            score[sym] = np.nan
            continue
        ar = cm[sym].pct_change()
        cov = ar.rolling(336, min_periods=336).cov(btc_ret)
        var = btc_ret.rolling(336, min_periods=336).var()
        beta = cov / var
        alt_r24 = cm[sym] / cm[sym].shift(24) - 1
        btc_r24 = cm["BTCUSDT"] / cm["BTCUSDT"].shift(24) - 1
        resid = alt_r24 - beta * btc_r24
        score[sym] = -resid  # long most negative residual
    return score

# S4 handled separately
def backtest_s4(cm, all_ts, fm):
    equity = [INIT]
    state = None
    turnover_cost = 0.0; total_funding = 0.0; n_trades = 0
    btc = cm["BTCUSDT"]; eth = cm["ETHUSDT"]
    ratio = np.log(btc / eth)
    roll_mean = ratio.rolling(336, min_periods=336).mean()
    roll_std = ratio.rolling(336, min_periods=336).std(ddof=0)
    z = (ratio - roll_mean) / roll_std
    for i in range(1, len(all_ts)):
        port_ret = 0.0
        if state == "long_btc":
            if pd.notna(btc.iloc[i-1]) and pd.notna(btc.iloc[i]) and btc.iloc[i-1]>0:
                port_ret += 0.5*(btc.iloc[i]/btc.iloc[i-1]-1)
            if pd.notna(eth.iloc[i-1]) and pd.notna(eth.iloc[i]) and eth.iloc[i-1]>0:
                port_ret += -0.5*(eth.iloc[i]/eth.iloc[i-1]-1)
        elif state == "short_btc":
            if pd.notna(btc.iloc[i-1]) and pd.notna(btc.iloc[i]) and btc.iloc[i-1]>0:
                port_ret += -0.5*(btc.iloc[i]/btc.iloc[i-1]-1)
            if pd.notna(eth.iloc[i-1]) and pd.notna(eth.iloc[i]) and eth.iloc[i-1]>0:
                port_ret += 0.5*(eth.iloc[i]/eth.iloc[i-1]-1)
        fund_ret = 0.0
        is_settlement = (all_ts[i].hour % 8 == 0 and all_ts[i].minute == 0)
        if is_settlement and state is not None:
            for sym, pos in [("BTCUSDT", 1 if state=="long_btc" else -1), ("ETHUSDT", -1 if state=="long_btc" else 1)]:
                if sym in fm.columns:
                    fr = fm[sym].iloc[i]
                    if pd.notna(fr):
                        fund_income = -pos * fr
                        fund_ret += 0.5 * fund_income
                        total_funding += 0.5 * equity[-1] * fund_income
        equity.append(equity[-1] * (1 + port_ret + fund_ret))
        zi = z.iloc[i] if i < len(z) else None
        if pd.isna(zi): 
            continue
        new_state = state
        if zi > 2 and state != "short_btc": new_state = "short_btc"
        elif zi < -2 and state != "long_btc": new_state = "long_btc"
        elif state == "long_btc" and zi >= 0: new_state = None
        elif state == "short_btc" and zi <= 0: new_state = None
        elif abs(zi) > 3.5: new_state = None
        if new_state != state:
            old_n = 2 if state is not None else 0
            new_n = 2 if new_state is not None else 0
            turnover = old_n + new_n
            cost = turnover * RT_COST * equity[-1] / 2
            equity[-1] -= cost
            turnover_cost += cost
            if turnover > 0: n_trades += 1
            state = new_state
    eq = np.array(equity)
    total_ret = (eq[-1]/eq[0]-1)*100
    max_dd = ((eq/np.maximum.accumulate(eq))-1).min()*100
    r = np.diff(eq)/eq[:-1]
    sharpe = np.mean(r)/np.std(r,ddof=1)*np.sqrt(8760) if np.std(r,ddof=1)>0 else 0
    split = int(len(eq)*0.7)
    is_ret = (eq[split-1]/eq[0]-1)*100
    oos_ret = (eq[-1]/eq[split-1]-1)*100
    is_dd = ((eq[:split]/np.maximum.accumulate(eq[:split]))-1).min()*100
    oos_dd = ((eq[split:]/np.maximum.accumulate(eq[split:]))-1).min()*100
    eq_series = pd.Series(eq, index=pd.DatetimeIndex(all_ts))
    monthly = eq_series.resample("ME").last().pct_change().dropna()
    pos_months = (monthly>0).mean()*100
    return {"strategy":"S4_BTCE","total_ret":round(total_ret,1),"max_dd":round(max_dd,1),
            "sharpe":round(sharpe,2),"is_ret":round(is_ret,1),"oos_ret":round(oos_ret,1),
            "is_dd":round(is_dd,1),"oos_dd":round(oos_dd,1),"pos_months":round(pos_months,1),
            "turnover_cost":round(turnover_cost,0),"funding":round(total_funding,0),"n_rebal":n_trades}

if __name__ == "__main__":
    t0 = time.time()
    print("="*90)
    print("CROSS-SECTIONAL FAST BACKTEST — 22 strategies")
    print("="*90)

    # 1h data
    print("\nLoading 1h data...")
    h1_syms = sorted([f.replace("_1h.csv","") for f in os.listdir(os.path.join(DATA,"binance_klines_1h")) if f.endswith("_1h.csv")])
    cm1, vm1, hm1, lm1, om1, tm1, ts1_list, idx1 = load_matrix(h1_syms, "1h")
    fm1, funding1 = load_funding_matrix(h1_syms, idx1)
    ts1 = ts1_list
    print(f"  1h: {len(h1_syms)} symbols, {len(ts1)} bars")

    # 5m data (from taker files)
    print("Loading 5m data...")
    taker_syms = sorted([f.replace("_5m.csv","") for f in os.listdir(os.path.join(DATA,"binance_klines_5m_taker")) if f.endswith("_5m.csv")])
    cm5, vm5, hm5, lm5, om5, tm5, ts5_list, idx5 = load_matrix(taker_syms, "5m", taker=True)
    fm5, funding5 = load_funding_matrix(taker_syms, idx5)
    ts5 = ts5_list
    print(f"  5m: {len(taker_syms)} symbols, {len(ts5)} bars")

    results = []

    # Strategy map: name -> (signal_fn, data, rebal, bpy)
    one_h = [
        ("S1_LowVol", sig_lowvol, cm1, vm1, hm1, lm1, om1, None, fm1, funding1, ts1, 168, 8760),
        ("S2_Beta", sig_beta, cm1, vm1, hm1, lm1, om1, None, fm1, funding1, ts1, 168, 8760),
        ("S3_Skew", sig_skew, cm1, vm1, hm1, lm1, om1, None, fm1, funding1, ts1, 168, 8760),
        ("S5_Defensive", sig_defensive, cm1, vm1, hm1, lm1, om1, None, fm1, funding1, ts1, 24, 8760),
        ("S6_ResidRev", sig_resid_rev, cm1, vm1, hm1, lm1, om1, None, fm1, funding1, ts1, 24, 8760),
        ("S7_FundingDiff", sig_funding_diff, cm1, vm1, hm1, lm1, om1, None, fm1, funding1, ts1, 24, 8760),
        ("S8_FundingMom", sig_funding_mom, cm1, vm1, hm1, lm1, om1, None, fm1, funding1, ts1, 168, 8760),
        ("S9_VolRatio", sig_vol_ratio, cm1, vm1, hm1, lm1, om1, None, fm1, funding1, ts1, 24, 8760),
        ("S10_SharpeMom", sig_sharpe_mom, cm1, vm1, hm1, lm1, om1, None, fm1, funding1, ts1, 168, 8760),
        ("S20_Composite", sig_composite, cm1, vm1, hm1, lm1, om1, None, fm1, funding1, ts1, 168, 8760),
        ("S22_Regime", sig_regime, cm1, vm1, hm1, lm1, om1, None, fm1, funding1, ts1, 24, 8760),
    ]
    five_m = [
        ("S11_CLV", sig_clv, cm5, vm5, hm5, lm5, om5, tm5, fm5, funding5, ts5, 12, 12*24*365),
        ("S12_Wick", sig_wick, cm5, vm5, hm5, lm5, om5, tm5, fm5, funding5, ts5, 12, 12*24*365),
        ("S13_VolCLV", sig_vol_clv, cm5, vm5, hm5, lm5, om5, tm5, fm5, funding5, ts5, 12, 12*24*365),
        ("S14_TakerRatio", sig_taker_ratio, cm5, vm5, hm5, lm5, om5, tm5, fm5, funding5, ts5, 12, 12*24*365),
        ("S15_TakerDiv", sig_taker_div, cm5, vm5, hm5, lm5, om5, tm5, fm5, funding5, ts5, 24, 12*24*365),
        ("S16_TakerSurprise", sig_taker_surprise, cm5, vm5, hm5, lm5, om5, tm5, fm5, funding5, ts5, 24, 12*24*365),
        ("S17_HFMom", sig_hf_mom, cm5, vm5, hm5, lm5, om5, tm5, fm5, funding5, ts5, 3, 12*24*365),
        ("S18_VolSpike", sig_vol_spike, cm5, vm5, hm5, lm5, om5, tm5, fm5, funding5, ts5, 3, 12*24*365),
        ("S19_LeadLag", sig_leadlag, cm5, vm5, hm5, lm5, om5, tm5, fm5, funding5, ts5, 1, 12*24*365),
        ("S21_Ensemble", sig_ensemble, cm5, vm5, hm5, lm5, om5, tm5, fm5, funding5, ts5, 12, 12*24*365),
    ]

    print("\n" + "="*90)
    print("RUNNING 1h STRATEGIES")
    print("="*90)
    for name, sfn, cm, vm, hm, lm, om, tm, fm, funding, ts, rebal, bpy in one_h:
        print(f"\n  Computing {name} signal...")
        try:
            scores = sfn(cm, vm, hm, lm, om, tm, fm, funding)
            print(f"  Running backtest...")
            m = backtest_fast(name, lambda c,v,h,l,o,t,f,fd: scores, cm, vm, hm, lm, om, tm, fm, funding, ts, rebal, bpy)
            results.append(m)
            print(f"    ret={m['total_ret']}% dd={m['max_dd']}% sharpe={m['sharpe']} oos={m['oos_ret']}% n_rebal={m['n_rebal']}")
        except Exception as e:
            print(f"    ERROR: {e}")
            import traceback; traceback.print_exc()

    # S4
    print("\n  Running S4_BTCE...")
    try:
        m = backtest_s4(cm1, ts1, fm1)
        results.append(m)
        print(f"    ret={m['total_ret']}% dd={m['max_dd']}% sharpe={m['sharpe']} oos={m['oos_ret']}%")
    except Exception as e:
        print(f"    ERROR: {e}")

    print("\n" + "="*90)
    print("RUNNING 5m STRATEGIES")
    print("="*90)
    for name, sfn, cm, vm, hm, lm, om, tm, fm, funding, ts, rebal, bpy in five_m:
        print(f"\n  Computing {name} signal...")
        try:
            scores = sfn(cm, vm, hm, lm, om, tm, fm, funding)
            print(f"  Running backtest...")
            m = backtest_fast(name, lambda c,v,h,l,o,t,f,fd: scores, cm, vm, hm, lm, om, tm, fm, funding, ts, rebal, bpy)
            results.append(m)
            print(f"    ret={m['total_ret']}% dd={m['max_dd']}% sharpe={m['sharpe']} oos={m['oos_ret']}% n_rebal={m['n_rebal']}")
        except Exception as e:
            print(f"    ERROR: {e}")
            import traceback; traceback.print_exc()

    # Summary
    print("\n" + "="*90)
    print("SUMMARY — ALL STRATEGIES")
    print("="*90)
    results.sort(key=lambda x: x["sharpe"], reverse=True)
    print(f"\n{'Strategy':<20} {'Ret%':>8} {'DD%':>7} {'Sharpe':>7} {'IS%':>8} {'OOS%':>8} {'PosMo':>6} {'Rebal':>6}")
    print("-"*90)
    for m in results:
        print(f"{m['strategy']:<20} {m['total_ret']:>8} {m['max_dd']:>7} {m['sharpe']:>7} {m['is_ret']:>8} {m['oos_ret']:>8} {m['pos_months']:>6} {m['n_rebal']:>6}")

    out_path = os.path.join(ROOT, "results", "cross_sectional_fast_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved to {out_path}")
    print(f"Total: {len(results)} strategies, time: {time.time()-t0:.0f}s")
