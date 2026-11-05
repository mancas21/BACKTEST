#!/usr/bin/env python
"""cross_sectional_strats.py — backtest engine for 22 cross-sectional/relative strategies."""
from __future__ import annotations
import json, os, sys, math
import numpy as np
import pandas as pd

ROOT = r"C:\Users\Lenovo\Documents\backtest-system"
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "code"))

INIT = 10000.0
COST_BPS = 5.0
SLIP_BPS = 3.0
RT_COST = (COST_BPS + SLIP_BPS) / 10000.0  # per side (per leg turn)

def load_ohlc(sym, tf):
    tf_map = {"1m":"binance_klines_1m", "5m":"binance_klines_5m",
              "15m":"binance_klines_15m", "1h":"binance_klines_1h"}
    ddir = tf_map[tf]
    p = os.path.join(DATA, ddir, f"{sym}_{tf}.csv")
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p)
    d.columns = [c.strip().lower() for c in d.columns]
    d["ts"] = pd.to_datetime(d["open_ts"], unit="ms", utc=True)
    d = d.sort_values("ts").reset_index(drop=True)
    return d

def load_taker(sym, tf):
    p = os.path.join(DATA, f"binance_klines_{tf}_taker", f"{sym}_{tf}.csv")
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
        if rate is None:
            continue
        rows.append({"ts": pd.to_datetime(t, unit="ms", utc=True), "rate": float(rate)})
    return pd.DataFrame(rows).sort_values("ts").reset_index(drop=True)

def ret_series(c, n):
    return c / c.shift(n) - 1.0

def realized_vol(c, n):
    return c.pct_change().rolling(n, min_periods=n).std(ddof=0)

def skewness(c, n):
    r = c.pct_change()
    return r.rolling(n, min_periods=n).skew()

def ols_beta(asset_ret, btc_ret, n):
    """Rolling OLS beta of asset returns on BTC returns."""
    cov = asset_ret.rolling(n, min_periods=n).cov(btc_ret)
    var = btc_ret.rolling(n, min_periods=n).var()
    return cov / var

def logret(c, n):
    return np.log(c / c.shift(n))

# ── Data loading ──────────────────────────────────────────────────────────────
# 1h universe
H1_SYMBOLS = ["ADAUSDT","AVAXUSDT","BNBUSDT","BTCUSDT","DOGEUSDT","ETHUSDT",
              "LINKUSDT","NEARUSDT","SOLUSDT","SUIUSDT","XRPUSDT"]
# Extended 1h (all available)
H1_ALL = []
for f in sorted(os.listdir(os.path.join(DATA, "binance_klines_1h"))):
    if f.endswith("_1h.csv"):
        H1_ALL.append(f.replace("_1h.csv",""))

FUNDING_SYMBOLS = ["BTCUSDT","ETHUSDT","HYPEUSDT","JUPUSDT","SOLUSDT",
                   "SPXUSDT","SUIUSDT","XRPUSDT"]

# 5m symbols
FIVE_M = []
for f in sorted(os.listdir(os.path.join(DATA, "binance_klines_5m"))):
    if f.endswith("_5m.csv"):
        FIVE_M.append(f.replace("_5m.csv",""))

# 5m taker symbols
FIVE_M_TAKER = []
for f in sorted(os.listdir(os.path.join(DATA, "binance_klines_5m_taker"))):
    if f.endswith("_5m.csv"):
        FIVE_M_TAKER.append(f.replace("_5m.csv",""))

def load_close_matrix(symbols, tf, taker=False):
    prices = {}
    for sym in symbols:
        if taker:
            df = load_taker(sym, tf)
        else:
            df = load_ohlc(sym, tf)
        if df is not None:
            prices[sym] = df
    if not prices:
        return None, None
    all_ts = sorted(set().union(*[set(prices[s]["ts"]) for s in prices]))
    close_matrix = pd.DataFrame(index=all_ts)
    vol_matrix = pd.DataFrame(index=all_ts)
    high_matrix = pd.DataFrame(index=all_ts)
    low_matrix = pd.DataFrame(index=all_ts)
    open_matrix = pd.DataFrame(index=all_ts)
    taker_matrix = pd.DataFrame(index=all_ts) if taker else None
    for sym in prices:
        d = prices[sym].set_index("ts")
        close_matrix[sym] = d["close"].reindex(all_ts)
        vol_matrix[sym] = d["volume"].reindex(all_ts)
        high_matrix[sym] = d["high"].reindex(all_ts)
        low_matrix[sym] = d["low"].reindex(all_ts)
        open_matrix[sym] = d["open"].reindex(all_ts)
        if taker and "taker_buy_base_vol" in d.columns:
            taker_matrix[sym] = d["taker_buy_base_vol"].reindex(all_ts)
    return (close_matrix, vol_matrix, high_matrix, low_matrix, open_matrix, taker_matrix, all_ts)

def load_funding_matrix(symbols, all_ts):
    funding = {}
    for sym in symbols:
        fd = load_funding(sym)
        if fd is not None:
            funding[sym] = fd
    fm = pd.DataFrame(index=all_ts)
    for sym in symbols:
        if sym in funding:
            f = funding[sym].set_index("ts")["rate"]
            fm[sym] = f.reindex(all_ts, method="ffill")
        else:
            fm[sym] = np.nan
    return fm, funding

# ── Weight functions (one per strategy) ────────────────────────────────────────

def weights_s1_lowvol(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=168):
    """S1: Low-Volatility Anomaly. Long 2 lowest vol, short 2 highest."""
    if i < 168:
        return {}
    vol = {}
    for sym in cm.columns:
        c = cm[sym].iloc[:i+1].dropna()
        if len(c) < 169:
            continue
        vol[sym] = c.pct_change().iloc[-168:].std(ddof=0)
    if len(vol) < 4:
        return {}
    ranked = sorted(vol, key=lambda s: vol[s])
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s2_beta(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=168):
    """S2: Beta-neutral low-beta. Long 2 lowest beta to BTC, short 2 highest."""
    if i < 336:
        return {}
    btc_ret = cm["BTCUSDT"].pct_change()
    beta = {}
    for sym in cm.columns:
        if sym == "BTCUSDT":
            continue
        ar = cm[sym].pct_change()
        b = ols_beta(ar, btc_ret, 336)
        val = b.iloc[i] if i < len(b) else None
        if pd.notna(val):
            beta[sym] = val
    if len(beta) < 4:
        return {}
    ranked = sorted(beta, key=lambda s: beta[s])
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s3_skew(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=168):
    """S3: Idiosyncratic skewness. Long 2 most negative skew, short 2 most positive."""
    if i < 168:
        return {}
    skew = {}
    for sym in cm.columns:
        c = cm[sym].iloc[:i+1].dropna()
        if len(c) < 169:
            continue
        r = c.pct_change().iloc[-168:]
        sk = r.skew()
        if pd.notna(sk):
            skew[sym] = sk
    if len(skew) < 4:
        return {}
    ranked = sorted(skew, key=lambda s: skew[s])
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s4_btce(cm, vm, hm, lm, om, tm, fm, funding, i, state=None):
    """S4: BTC/ETH ratio z-score. Stateful: need to track position."""
    # Handled specially in backtest loop
    return {}

def weights_s10_sharpe_mom(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=168):
    """S10: Sharpe-momentum. Long top 2 by 168-bar ROC/vol, short bottom 2. Gate: 336-bar ROC > 0 for longs."""
    if i < 336:
        return {}
    score = {}
    roc336 = {}
    for sym in cm.columns:
        c = cm[sym].iloc[:i+1].dropna()
        if len(c) < 337:
            continue
        r168 = c.iloc[-1]/c.iloc[-1-168] - 1
        vol168 = c.pct_change().iloc[-168:].std(ddof=0)
        if vol168 > 0:
            score[sym] = r168 / vol168
        roc336[sym] = c.iloc[-1]/c.iloc[-1-336] - 1
    long_cands = [s for s in score if roc336.get(s,0) > 0]
    short_cands = [s for s in score if roc336.get(s,0) < 0]
    if len(long_cands) < 2 or len(short_cands) < 2:
        return {}
    long_ranked = sorted(long_cands, key=lambda s: score[s], reverse=True)
    short_ranked = sorted(short_cands, key=lambda s: score[s])
    longs = long_ranked[:2]
    shorts = short_ranked[:2]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s7_funding_diff(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=24):
    """S7: Cross-sectional funding differential. Long 2 most negative funding, short 2 most positive."""
    if i < 24:
        return {}
    fr = {}
    for sym in cm.columns:
        if sym in fm.columns:
            r = fm[sym].iloc[i]
            if pd.notna(r):
                fr[sym] = r
    if len(fr) < 4:
        return {}
    ranked = sorted(fr, key=lambda s: fr[s])
    longs = ranked[:2]   # most negative
    shorts = ranked[-2:]  # most positive
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s8_funding_mom(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=168):
    """S8: Funding-filtered momentum. Long top-half ROC with funding<0, short bottom-half ROC with funding>0."""
    if i < 336:
        return {}
    roc = {}
    fr = {}
    for sym in cm.columns:
        c = cm[sym].iloc[:i+1].dropna()
        if len(c) < 337:
            continue
        roc[sym] = c.iloc[-1]/c.iloc[-1-168] - 1
        if sym in fm.columns:
            r = fm[sym].iloc[i]
            if pd.notna(r):
                fr[sym] = r
    if len(roc) < 4:
        return {}
    med = np.median(list(roc.values()))
    long_cands = [s for s in roc if roc[s] > med and fr.get(s, 0) < 0]
    short_cands = [s for s in roc if roc[s] < med and fr.get(s, 0) > 0]
    # fill to 2 per side from next-best
    if len(long_cands) < 2:
        extras = sorted([s for s in roc if s not in long_cands and fr.get(s,0) < 0], key=lambda s: roc[s], reverse=True)
        long_cands = long_cands + extras[:2-len(long_cands)]
    if len(short_cands) < 2:
        extras = sorted([s for s in roc if s not in short_cands and fr.get(s,0) > 0], key=lambda s: roc[s])
        short_cands = short_cands + extras[:2-len(short_cands)]
    if len(long_cands) < 2 or len(short_cands) < 2:
        return {}
    long_ranked = sorted(long_cands, key=lambda s: roc[s], reverse=True)[:2]
    short_ranked = sorted(short_cands, key=lambda s: roc[s])[:2]
    w = {}
    for s in long_ranked: w[s] = 0.5/len(long_ranked)
    for s in short_ranked: w[s] = -0.5/len(short_ranked)
    return w

def weights_s9_vol_ratio(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=24):
    """S9: Volatility risk premium. Long 2 lowest vol ratio (24/168), short 2 highest."""
    if i < 168:
        return {}
    vr = {}
    for sym in cm.columns:
        c = cm[sym].iloc[:i+1].dropna()
        if len(c) < 169:
            continue
        v24 = c.pct_change().iloc[-24:].std(ddof=0)
        v168 = c.pct_change().iloc[-168:].std(ddof=0)
        if v168 > 0:
            vr[sym] = v24 / v168
    if len(vr) < 4:
        return {}
    ranked = sorted(vr, key=lambda s: vr[s])
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s11_clv(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=12):
    """S11: Close-location value. Long 2 highest mean CLV over 12 bars, short 2 lowest."""
    if i < 12:
        return {}
    clv = {}
    for sym in cm.columns:
        if sym not in hm.columns:
            continue
        h = hm[sym].iloc[max(0,i-11):i+1]
        l = lm[sym].iloc[max(0,i-11):i+1]
        c = cm[sym].iloc[max(0,i-11):i+1]
        vals = []
        for j in range(len(c)):
            hi = h.iloc[j]; lo = l.iloc[j]; cl = c.iloc[j]
            rng = hi - lo
            if rng > 0:
                vals.append((cl - lo) / rng)
            else:
                vals.append(0.5)
        if vals:
            clv[sym] = np.mean(vals)
    if len(clv) < 4:
        return {}
    ranked = sorted(clv, key=lambda s: clv[s], reverse=True)
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s12_wick(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=12):
    """S12: Wick-rejection ratio. Long 2 highest wick score, short 2 lowest."""
    if i < 12:
        return {}
    score = {}
    for sym in cm.columns:
        if sym not in hm.columns:
            continue
        h = hm[sym].iloc[max(0,i-11):i+1].values
        l = lm[sym].iloc[max(0,i-11):i+1].values
        o = om[sym].iloc[max(0,i-11):i+1].values
        c = cm[sym].iloc[max(0,i-11):i+1].values
        lower_wick = np.sum(np.minimum(o, c) - l)
        upper_wick = np.sum(h - np.maximum(o, c))
        rng = np.sum(h - l)
        if rng > 0:
            score[sym] = (lower_wick - upper_wick) / rng
    if len(score) < 4:
        return {}
    ranked = sorted(score, key=lambda s: score[s], reverse=True)
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s13_vol_clv(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=12):
    """S13: Volume-weighted CLV (accumulation/distribution)."""
    if i < 24:
        return {}
    score = {}
    for sym in cm.columns:
        if sym not in hm.columns or sym not in vm.columns:
            continue
        h = hm[sym].iloc[max(0,i-23):i+1].values
        l = lm[sym].iloc[max(0,i-23):i+1].values
        c = cm[sym].iloc[max(0,i-23):i+1].values
        v = vm[sym].iloc[max(0,i-23):i+1].values
        clvs = []
        for j in range(len(c)):
            rng = h[j]-l[j]
            clv = (c[j]-l[j])/rng if rng>0 else 0.5
            clvs.append(clv)
        clvs = np.array(clvs)
        vsum = np.sum(v)
        if vsum > 0:
            score[sym] = np.sum(clvs * v) / vsum
    if len(score) < 4:
        return {}
    ranked = sorted(score, key=lambda s: score[s], reverse=True)
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s14_taker_ratio(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=12):
    """S14: Taker buy ratio cross-sectional. Long 2 highest mean TBR, short 2 lowest."""
    if tm is None or i < 12:
        return {}
    tbr = {}
    for sym in cm.columns:
        if sym not in tm.columns:
            continue
        t = tm[sym].iloc[max(0,i-11):i+1].values
        v = vm[sym].iloc[max(0,i-11):i+1].values
        tbrs = []
        for j in range(len(t)):
            if v[j] > 0:
                tbrs.append(t[j]/v[j])
        if tbrs:
            tbr[sym] = np.mean(tbrs)
    if len(tbr) < 4:
        return {}
    ranked = sorted(tbr, key=lambda s: tbr[s], reverse=True)
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s15_taker_div(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=24):
    """S15: Taker flow / price divergence."""
    if tm is None or i < 48:
        return {}
    score = {}
    for sym in cm.columns:
        if sym not in tm.columns:
            continue
        c = cm[sym].iloc[max(0,i-47):i+1].values
        t = tm[sym].iloc[max(0,i-47):i+1].values
        v = vm[sym].iloc[max(0,i-47):i+1].values
        if len(c) < 48:
            continue
        r = c[-1]/c[-25] - 1 if len(c) >= 25 else 0  # 24-bar return approx
        r24 = c[-1]/c[-25]-1 if len(c)>=25 else 0
        tbr_recent = []
        tbr_prior = []
        for j in range(len(t)):
            if v[j] > 0:
                ratio = t[j]/v[j]
                if j >= len(t)-24:
                    tbr_recent.append(ratio)
                else:
                    tbr_prior.append(ratio)
        if not tbr_recent or not tbr_prior:
            continue
        dtbr = np.mean(tbr_recent) - np.mean(tbr_prior)
        # z-score over 168-bar window (simplified: use raw diff)
        score[sym] = dtbr - r24  # flow up, price down = accumulation
    if len(score) < 4:
        return {}
    ranked = sorted(score, key=lambda s: score[s], reverse=True)
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s16_taker_surprise(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=24):
    """S16: Taker-flow surprise. Z-score of mean TBR vs 168-bar history."""
    if tm is None or i < 168:
        return {}
    score = {}
    for sym in cm.columns:
        if sym not in tm.columns:
            continue
        t = tm[sym].iloc[:i+1].values
        v = vm[sym].iloc[:i+1].values
        if len(t) < 169:
            continue
        # recent 24-bar mean TBR
        recent_tbr = []
        for j in range(max(0,i-23), i+1):
            if v[j] > 0:
                recent_tbr.append(t[j]/v[j])
        if not recent_tbr:
            continue
        recent_mean = np.mean(recent_tbr)
        # historical TBR series
        hist_tbr = []
        for j in range(max(0,i-167), i+1):
            if v[j] > 0:
                hist_tbr.append(t[j]/v[j])
        if len(hist_tbr) < 50:
            continue
        hist_mean = np.mean(hist_tbr)
        hist_std = np.std(hist_tbr, ddof=0)
        if hist_std > 0:
            score[sym] = (recent_mean - hist_mean) / hist_std
    if len(score) < 4:
        return {}
    ranked = sorted(score, key=lambda s: score[s], reverse=True)
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s17_hf_mom(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=3):
    """S17: HF cross-sectional momentum (12-bar return). Hysteresis: swap only if new candidate outranks by >=2."""
    if i < 12:
        return {}
    roc = {}
    for sym in cm.columns:
        c = cm[sym].iloc[:i+1].dropna()
        if len(c) < 13:
            continue
        roc[sym] = c.iloc[-1]/c.iloc[-13] - 1  # 12-bar return
    if len(roc) < 4:
        return {}
    ranked = sorted(roc, key=lambda s: roc[s], reverse=True)
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s18_vol_spike(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=3):
    """S18: Relative volume spike. Long 2 highest vol ratio, short 2 lowest."""
    if i < 168:
        return {}
    vr = {}
    for sym in cm.columns:
        if sym not in vm.columns:
            continue
        v = vm[sym].iloc[:i+1].dropna()
        if len(v) < 169:
            continue
        recent = v.iloc[-3:].mean()
        avg = v.iloc[-168:].mean()
        if avg > 0:
            vr[sym] = recent / avg
    if len(vr) < 4:
        return {}
    ranked = sorted(vr, key=lambda s: vr[s], reverse=True)
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s19_leadlag(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=1):
    """S19: BTC lead-lag residual reversion. Long 2 most negative residual, short 2 most positive."""
    if i < 336 or "BTCUSDT" not in cm.columns:
        return {}
    # compute beta vs BTC
    btc_ret = cm["BTCUSDT"].pct_change()
    beta = {}
    for sym in cm.columns:
        if sym == "BTCUSDT":
            continue
        ar = cm[sym].pct_change()
        b = ols_beta(ar, btc_ret, 336)
        val = b.iloc[i] if i < len(b) else None
        if pd.notna(val):
            beta[sym] = val
    # 3-bar cumulative residual
    resid = {}
    for sym in cm.columns:
        if sym == "BTCUSDT" or sym not in beta:
            continue
        c = cm[sym].iloc[max(0,i-2):i+1].values
        b = beta[sym]
        btc_c = cm["BTCUSDT"].iloc[max(0,i-2):i+1].values
        if len(c) < 3 or len(btc_c) < 3:
            continue
        res = 0.0
        for j in range(1, len(c)):
            r_alt = c[j]/c[j-1] - 1
            r_btc = btc_c[j]/btc_c[j-1] - 1
            res += r_alt - b * r_btc
        resid[sym] = res
    if len(resid) < 4:
        return {}
    # threshold: |residual| > 0.5 * 168-bar std of residual
    # simplified: just rank
    ranked = sorted(resid, key=lambda s: resid[s])
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s20_composite(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=168):
    """S20: Sharpe-momentum + funding composite. z(ROC/vol) - z(funding)."""
    if i < 336:
        return {}
    score = {}
    fr = {}
    for sym in cm.columns:
        c = cm[sym].iloc[:i+1].dropna()
        if len(c) < 337:
            continue
        r168 = c.iloc[-1]/c.iloc[-1-168] - 1
        vol168 = c.pct_change().iloc[-168:].std(ddof=0)
        if vol168 <= 0:
            continue
        sharpe_mom = r168 / vol168
        score[sym] = sharpe_mom
        if sym in fm.columns:
            r = fm[sym].iloc[i]
            if pd.notna(r):
                fr[sym] = r
    if len(score) < 4:
        return {}
    # z-score the components
    vals = list(score.values())
    smean = np.mean(vals); sstd = np.std(vals, ddof=0)
    fvals = [fr.get(s, 0) for s in score]
    fmean = np.mean(fvals); fstd = np.std(fvals, ddof=0)
    composite = {}
    for s in score:
        z_sm = (score[s] - smean) / sstd if sstd > 0 else 0
        z_f = (fr.get(s, 0) - fmean) / fstd if fstd > 0 else 0
        composite[s] = z_sm - z_f
    ranked = sorted(composite, key=lambda s: composite[s], reverse=True)
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s21_ensemble(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=24):
    """S21: Multi-factor ensemble (momentum + taker flow + low-vol). 7 taker symbols."""
    if tm is None or i < 168:
        return {}
    # momentum rank
    roc = {}
    for sym in cm.columns:
        if sym not in tm.columns:
            continue
        c = cm[sym].iloc[:i+1].dropna()
        if len(c) < 169:
            continue
        roc[sym] = c.iloc[-1]/c.iloc[-1-168] - 1
    if len(roc) < 4:
        return {}
    # taker flow rank (24-bar mean TBR)
    tbr = {}
    for sym in cm.columns:
        if sym not in tm.columns:
            continue
        t = tm[sym].iloc[max(0,i-23):i+1].values
        v = vm[sym].iloc[max(0,i-23):i+1].values
        tbrs = [t[j]/v[j] for j in range(len(t)) if v[j]>0]
        if tbrs:
            tbr[sym] = np.mean(tbrs)
    # vol rank
    vol = {}
    for sym in cm.columns:
        if sym not in tm.columns:
            continue
        c = cm[sym].iloc[:i+1].dropna()
        if len(c) < 169:
            continue
        vol[sym] = c.pct_change().iloc[-168:].std(ddof=0)
    # composite = 1/3 rank(roc) + 1/3 rank(tbr) + 1/3 rank(-vol)
    common = [s for s in roc if s in tbr and s in vol]
    if len(common) < 4:
        return {}
    def rank_dict(d, reverse=True):
        items = sorted(d.items(), key=lambda x: x[1], reverse=reverse)
        return {s: r for r, (s, _) in enumerate(items)}
    r_roc = rank_dict({s: roc[s] for s in common}, True)
    r_tbr = rank_dict({s: tbr[s] for s in common}, True)
    r_vol = rank_dict({s: vol[s] for s in common}, False)  # low vol = high rank
    composite = {}
    for s in common:
        composite[s] = r_roc[s] + r_tbr[s] + r_vol[s]
    # lower composite = better (ranks are 0-based, lower is better)
    ranked = sorted(composite, key=lambda s: composite[s])
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s22_regime(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=24):
    """S22: Regime-switching factor weights. Momentum + low-vol, weights depend on regime."""
    if i < 336:
        return {}
    # regime: cross-sectional median 168-bar vol vs its own 336-bar median
    vols = []
    for sym in cm.columns:
        c = cm[sym].iloc[:i+1].dropna()
        if len(c) < 169:
            continue
        vols.append(c.pct_change().iloc[-168:].std(ddof=0))
    if not vols:
        return {}
    med_vol = np.median(vols)
    # 336-bar median of the cross-sectional median vol
    hist_med_vols = []
    for j in range(max(168, i-335), i+1):
        vs = []
        for sym in cm.columns:
            c = cm[sym].iloc[:j+1].dropna()
            if len(c) < 169:
                continue
            vs.append(c.pct_change().iloc[-168:].std(ddof=0))
        if vs:
            hist_med_vols.append(np.median(vs))
    regime_med = np.median(hist_med_vols) if hist_med_vols else med_vol
    if med_vol <= regime_med:
        w_mom, w_vol = 0.7, 0.3
    else:
        w_mom, w_vol = 0.3, 0.7
    # composite
    roc = {}; vol = {}
    for sym in cm.columns:
        c = cm[sym].iloc[:i+1].dropna()
        if len(c) < 337:
            continue
        roc[sym] = c.iloc[-1]/c.iloc[-1-168] - 1
        vol[sym] = c.pct_change().iloc[-168:].std(ddof=0)
    common = [s for s in roc if s in vol]
    if len(common) < 4:
        return {}
    def rank_dict(d, reverse=True):
        items = sorted(d.items(), key=lambda x: x[1], reverse=reverse)
        return {s: r for r, (s, _) in enumerate(items)}
    r_roc = rank_dict({s: roc[s] for s in common}, True)
    r_vol = rank_dict({s: vol[s] for s in common}, False)
    composite = {}
    for s in common:
        composite[s] = w_mom * r_roc[s] + w_vol * r_vol[s]
    ranked = sorted(composite, key=lambda s: composite[s])
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s5_defensive(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=24):
    """S5: Relative-strength-during-correction. Trigger: BTC 24h < -3%. Long 2 highest beta-adj return, short 2 lowest."""
    if i < 336 or "BTCUSDT" not in cm.columns:
        return {}
    btc_ret24 = cm["BTCUSDT"].iloc[i]/cm["BTCUSDT"].iloc[max(0,i-24)] - 1
    if btc_ret24 >= -0.03:
        return {}  # not in correction
    # beta from 336-bar regression
    btc_ret = cm["BTCUSDT"].pct_change()
    beta_adj = {}
    for sym in cm.columns:
        if sym == "BTCUSDT":
            continue
        ar = cm[sym].pct_change()
        b = ols_beta(ar, btc_ret, 336)
        val = b.iloc[i] if i < len(b) else None
        if not pd.notna(val):
            continue
        alt_ret24 = cm[sym].iloc[i]/cm[sym].iloc[max(0,i-24)] - 1
        beta_adj[sym] = alt_ret24 - val * btc_ret24
    if len(beta_adj) < 4:
        return {}
    ranked = sorted(beta_adj, key=lambda s: beta_adj[s], reverse=True)
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

def weights_s6_resid_rev(cm, vm, hm, lm, om, tm, fm, funding, i, rebal_every=24):
    """S6: Beta-adjusted residual reversal. Long 2 lowest residual 24-bar, short 2 highest."""
    if i < 336 or "BTCUSDT" not in cm.columns:
        return {}
    btc_ret = cm["BTCUSDT"].pct_change()
    resid = {}
    for sym in cm.columns:
        if sym == "BTCUSDT":
            continue
        ar = cm[sym].pct_change()
        b = ols_beta(ar, btc_ret, 336)
        val = b.iloc[i] if i < len(b) else None
        if not pd.notna(val):
            continue
        # residual 24-bar return
        alt_r24 = cm[sym].iloc[i]/cm[sym].iloc[max(0,i-24)] - 1
        btc_r24 = cm["BTCUSDT"].iloc[i]/cm["BTCUSDT"].iloc[max(0,i-24)] - 1
        resid[sym] = alt_r24 - val * btc_r24
    if len(resid) < 4:
        return {}
    ranked = sorted(resid, key=lambda s: resid[s])
    longs = ranked[:2]
    shorts = ranked[-2:]
    w = {}
    for s in longs: w[s] = 0.5/len(longs)
    for s in shorts: w[s] = -0.5/len(shorts)
    return w

# ── Backtest engine ────────────────────────────────────────────────────────────
def backtest_strategy(strategy_name, weight_fn, cm, vm, hm, lm, om, tm, fm, funding, all_ts, rebal_every, bars_per_year=8760):
    """Generic cross-sectional backtest."""
    equity = [INIT]
    positions = {}
    last_rebal = 0
    turnover_cost = 0.0
    total_funding = 0.0
    n_rebalances = 0

    for i in range(1, len(all_ts)):
        port_ret = 0.0
        n_pos = len(positions)
        if n_pos > 0:
            for sym, pos in positions.items():
                if sym in cm.columns:
                    c_prev = cm[sym].iloc[i-1]
                    c_curr = cm[sym].iloc[i]
                    if pd.notna(c_prev) and pd.notna(c_curr) and c_prev > 0:
                        port_ret += (1.0/n_pos) * pos * (c_curr / c_prev - 1)

        # funding at settlement (8h)
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

        # rebalance
        if i - last_rebal >= rebal_every or not positions:
            new_weights = weight_fn(cm, vm, hm, lm, om, tm, fm, funding, i)
            if not new_weights:
                last_rebal = i
                continue
            new_positions = {s: (1 if w > 0 else -1) for s, w in new_weights.items()}
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
    sharpe = np.mean(r) / np.std(r, ddof=1) * np.sqrt(bars_per_year) if np.std(r, ddof=1) > 0 else 0

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

# ── Strategy registry ──────────────────────────────────────────────────────────
STRATS = [
    # (name, weight_fn, data_tf, rebal_every, bars_per_year, use_taker)
    ("S1_LowVol", weights_s1_lowvol, "1h", 168, 8760, False),
    ("S2_Beta", weights_s2_beta, "1h", 168, 8760, False),
    ("S3_Skew", weights_s3_skew, "1h", 168, 8760, False),
    ("S5_Defensive", weights_s5_defensive, "1h", 24, 8760, False),
    ("S6_ResidRev", weights_s6_resid_rev, "1h", 24, 8760, False),
    ("S7_FundingDiff", weights_s7_funding_diff, "1h", 24, 8760, False),
    ("S8_FundingMom", weights_s8_funding_mom, "1h", 168, 8760, False),
    ("S9_VolRatio", weights_s9_vol_ratio, "1h", 24, 8760, False),
    ("S10_SharpeMom", weights_s10_sharpe_mom, "1h", 168, 8760, False),
    ("S11_CLV", weights_s11_clv, "5m", 12, 12*24*365, False),
    ("S12_Wick", weights_s12_wick, "5m", 12, 12*24*365, False),
    ("S13_VolCLV", weights_s13_vol_clv, "5m", 12, 12*24*365, False),
    ("S14_TakerRatio", weights_s14_taker_ratio, "5m", 12, 12*24*365, True),
    ("S15_TakerDiv", weights_s15_taker_div, "5m", 24, 12*24*365, True),
    ("S16_TakerSurprise", weights_s16_taker_surprise, "5m", 24, 12*24*365, True),
    ("S17_HFMom", weights_s17_hf_mom, "5m", 3, 12*24*365, False),
    ("S18_VolSpike", weights_s18_vol_spike, "5m", 3, 12*24*365, False),
    ("S19_LeadLag", weights_s19_leadlag, "5m", 1, 12*24*365, False),
    ("S20_Composite", weights_s20_composite, "1h", 168, 8760, False),
    ("S21_Ensemble", weights_s21_ensemble, "1h", 24, 8760, True),
    ("S22_Regime", weights_s22_regime, "1h", 24, 8760, False),
]

# S4 is BTC/ETH ratio z-score — handled separately
def backtest_s4(cm, all_ts, fm):
    """S4: BTC/ETH ratio z-score. Stateful."""
    equity = [INIT]
    positions = {}  # 'long_btc_short_eth' or 'short_btc_long_eth'
    state = None  # None, 'long_btc', 'short_btc'
    last_check = 0
    turnover_cost = 0.0
    total_funding = 0.0
    n_trades = 0

    btc = cm["BTCUSDT"]; eth = cm["ETHUSDT"]
    # precompute z-score
    ratio = np.log(btc / eth)
    roll_mean = ratio.rolling(336, min_periods=336).mean()
    roll_std = ratio.rolling(336, min_periods=336).std(ddof=0)
    z = (ratio - roll_mean) / roll_std

    for i in range(1, len(all_ts)):
        port_ret = 0.0
        n_pos = len(positions)
        if n_pos > 0 and state is not None:
            if state == "long_btc":
                # long BTC, short ETH
                if pd.notna(btc.iloc[i-1]) and pd.notna(btc.iloc[i]) and btc.iloc[i-1]>0:
                    port_ret += 0.5 * (btc.iloc[i]/btc.iloc[i-1] - 1)
                if pd.notna(eth.iloc[i-1]) and pd.notna(eth.iloc[i]) and eth.iloc[i-1]>0:
                    port_ret += -0.5 * (eth.iloc[i]/eth.iloc[i-1] - 1)
            elif state == "short_btc":
                if pd.notna(btc.iloc[i-1]) and pd.notna(btc.iloc[i]) and btc.iloc[i-1]>0:
                    port_ret += -0.5 * (btc.iloc[i]/btc.iloc[i-1] - 1)
                if pd.notna(eth.iloc[i-1]) and pd.notna(eth.iloc[i]) and eth.iloc[i-1]>0:
                    port_ret += 0.5 * (eth.iloc[i]/eth.iloc[i-1] - 1)

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

        # check signal
        zi = z.iloc[i] if i < len(z) else None
        if pd.isna(zi):
            continue
        new_state = state
        if zi > 2 and state != "short_btc":
            new_state = "short_btc"
        elif zi < -2 and state != "long_btc":
            new_state = "long_btc"
        elif state == "long_btc" and zi >= 0:
            new_state = None
        elif state == "short_btc" and zi <= 0:
            new_state = None
        elif abs(zi) > 3.5:
            new_state = None  # stop

        if new_state != state:
            # turnover
            old_n = 2 if state is not None else 0
            new_n = 2 if new_state is not None else 0
            turnover = old_n + new_n  # all legs change
            cost = turnover * RT_COST * equity[-1] / 2
            equity[-1] -= cost
            turnover_cost += cost
            if turnover > 0:
                n_trades += 1
            state = new_state

    eq = np.array(equity)
    total_ret = (eq[-1]/eq[0] - 1) * 100
    max_dd = ((eq / np.maximum.accumulate(eq)) - 1).min() * 100
    r = np.diff(eq) / eq[:-1]
    sharpe = np.mean(r) / np.std(r, ddof=1) * np.sqrt(8760) if np.std(r, ddof=1) > 0 else 0
    split = int(len(eq) * 0.7)
    is_ret = (eq[split-1]/eq[0] - 1) * 100
    oos_ret = (eq[-1]/eq[split-1] - 1) * 100
    is_dd = ((eq[:split] / np.maximum.accumulate(eq[:split])) - 1).min() * 100
    oos_dd = ((eq[split:] / np.maximum.accumulate(eq[split:])) - 1).min() * 100
    eq_series = pd.Series(eq, index=pd.DatetimeIndex(all_ts))
    monthly = eq_series.resample("ME").last().pct_change().dropna()
    pos_months = (monthly > 0).mean() * 100
    return {
        "strategy": "S4_BTCE",
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
        "n_rebal": n_trades,
    }

if __name__ == "__main__":
    print("=" * 90)
    print("CROSS-SECTIONAL STRATEGY BACKTEST — 22 strategies")
    print("=" * 90)

    # Load 1h data
    print("\nLoading 1h data...")
    h1_syms = H1_ALL if len(H1_ALL) >= 11 else H1_SYMBOLS
    cm1, vm1, hm1, lm1, om1, tm1, ts1 = load_close_matrix(h1_syms, "1h")
    fm1, funding1 = load_funding_matrix(h1_syms, ts1)
    print(f"  1h: {len(h1_syms)} symbols, {len(ts1)} bars")

    # Load 5m data (use taker data as primary source since it has OHLCV + taker volume)
    print("Loading 5m data (from taker files)...")
    cm5, vm5, hm5, lm5, om5, tm5, ts5 = load_close_matrix(FIVE_M_TAKER, "5m", taker=True)
    fm5, funding5 = load_funding_matrix(FIVE_M_TAKER, ts5)
    print(f"  5m: {len(FIVE_M_TAKER)} symbols, {len(ts5)} bars")

    # Load 5m taker data
    print("Loading 5m taker data...")
    cmt, vmt, hmt, lmt, omt, tmt, tst = load_close_matrix(FIVE_M_TAKER, "5m", taker=True)
    fmt_t, fundingt = load_funding_matrix(FIVE_M_TAKER, tst)
    print(f"  5m taker: {len(FIVE_M_TAKER)} symbols, {len(tst)} bars")

    results = []

    # Run 1h strategies (non-taker)
    print("\n" + "=" * 90)
    print("RUNNING 1h STRATEGIES")
    print("=" * 90)
    one_h_strats = [s for s in STRATS if s[2] == "1h" and not s[5]]
    for name, wfn, tf, rebal, bpy, use_taker in one_h_strats:
        print(f"\n  Running {name}...")
        try:
            m = backtest_strategy(name, wfn, cm1, vm1, hm1, lm1, om1, None, fm1, funding1, ts1, rebal, bpy)
            results.append(m)
            print(f"    ret={m['total_ret']}% dd={m['max_dd']}% sharpe={m['sharpe']} oos={m['oos_ret']}% n_rebal={m['n_rebal']}")
        except Exception as e:
            print(f"    ERROR: {e}")
            import traceback; traceback.print_exc()

    # Run 1h strategies (taker-based, use taker data resampled? No, use 1h prices + funding)
    # S21 ensemble uses taker data on 1h timeframe — use taker universe
    print("\n" + "=" * 90)
    print("RUNNING 1h TAKER-BASED STRATEGIES")
    print("=" * 90)
    # S21 needs taker data but on 1h timeframe — skip for now, run with 5m taker
    # Actually S21 is multi-TF; let's run it on 5m taker universe with 1h rebal (24 bars of 5m = 2h... no)
    # S21 rebal_every=24 bars, but on 5m that's 2h. The spec says daily (24 bars on 1h = 1 day).
    # For simplicity, run S21 on 1h data with taker data not available at 1h.
    # We'll skip S21 for now and note it.

    # Run S4 (BTC/ETH ratio)
    print("\n  Running S4_BTCE...")
    try:
        m = backtest_s4(cm1, ts1, fm1)
        results.append(m)
        print(f"    ret={m['total_ret']}% dd={m['max_dd']}% sharpe={m['sharpe']} oos={m['oos_ret']}%")
    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback; traceback.print_exc()

    # Run S20 (composite, 1h)
    print("\n  Running S20_Composite...")
    try:
        m = backtest_strategy("S20_Composite", weights_s20_composite, cm1, vm1, hm1, lm1, om1, None, fm1, funding1, ts1, 168, 8760)
        results.append(m)
        print(f"    ret={m['total_ret']}% dd={m['max_dd']}% sharpe={m['sharpe']} oos={m['oos_ret']}%")
    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback; traceback.print_exc()

    # Run S22 (regime, 1h)
    print("\n  Running S22_Regime...")
    try:
        m = backtest_strategy("S22_Regime", weights_s22_regime, cm1, vm1, hm1, lm1, om1, None, fm1, funding1, ts1, 24, 8760)
        results.append(m)
        print(f"    ret={m['total_ret']}% dd={m['max_dd']}% sharpe={m['sharpe']} oos={m['oos_ret']}%")
    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback; traceback.print_exc()

    # Run 5m strategies (non-taker)
    print("\n" + "=" * 90)
    print("RUNNING 5m STRATEGIES")
    print("=" * 90)
    five_m_strats = [s for s in STRATS if s[2] == "5m" and not s[5]]
    for name, wfn, tf, rebal, bpy, use_taker in five_m_strats:
        print(f"\n  Running {name}...")
        try:
            m = backtest_strategy(name, wfn, cm5, vm5, hm5, lm5, om5, None, fm5, funding5, ts5, rebal, bpy)
            results.append(m)
            print(f"    ret={m['total_ret']}% dd={m['max_dd']}% sharpe={m['sharpe']} oos={m['oos_ret']}% n_rebal={m['n_rebal']}")
        except Exception as e:
            print(f"    ERROR: {e}")
            import traceback; traceback.print_exc()

    # Run 5m taker strategies
    print("\n" + "=" * 90)
    print("RUNNING 5m TAKER STRATEGIES")
    print("=" * 90)
    taker_strats = [s for s in STRATS if s[5]]
    for name, wfn, tf, rebal, bpy, use_taker in taker_strats:
        print(f"\n  Running {name}...")
        try:
            m = backtest_strategy(name, wfn, cmt, vmt, hmt, lmt, omt, tmt, fmt_t, fundingt, tst, rebal, bpy)
            results.append(m)
            print(f"    ret={m['total_ret']}% dd={m['max_dd']}% sharpe={m['sharpe']} oos={m['oos_ret']}% n_rebal={m['n_rebal']}")
        except Exception as e:
            print(f"    ERROR: {e}")
            import traceback; traceback.print_exc()

    # Run S21 on taker universe (1h rebal = 12 bars of 5m? No, 24 bars of 5m = 2h. Spec says daily.)
    # Run with 12-bar rebal (1h) on 5m data as approximation
    print("\n  Running S21_Ensemble (on 5m taker, 12-bar rebal)...")
    try:
        m = backtest_strategy("S21_Ensemble", weights_s21_ensemble, cmt, vmt, hmt, lmt, omt, tmt, fmt_t, fundingt, tst, 12, 12*24*365)
        results.append(m)
        print(f"    ret={m['total_ret']}% dd={m['max_dd']}% sharpe={m['sharpe']} oos={m['oos_ret']}%")
    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback; traceback.print_exc()

    # Summary
    print("\n" + "=" * 90)
    print("SUMMARY — ALL STRATEGIES")
    print("=" * 90)
    results.sort(key=lambda x: x["sharpe"], reverse=True)
    print(f"\n{'Strategy':<20} {'Ret%':>8} {'DD%':>7} {'Sharpe':>7} {'IS%':>8} {'OOS%':>8} {'PosMo':>6} {'Rebal':>6}")
    print("-" * 90)
    for m in results:
        print(f"{m['strategy']:<20} {m['total_ret']:>8} {m['max_dd']:>7} {m['sharpe']:>7} {m['is_ret']:>8} {m['oos_ret']:>8} {m['pos_months']:>6} {m['n_rebal']:>6}")

    # Save
    out_path = os.path.join(ROOT, "results", "cross_sectional_strats_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved to {out_path}")
    print(f"Total strategies run: {len(results)}")
