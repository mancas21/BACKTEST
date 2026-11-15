"""
CRYPTO STRATEGY PACK - 20 backtest-ready strategies
====================================================
Every strategy implements the same contract:

    signals = STRATEGIES["name"](df)   ->  DataFrame indexed like df with columns
        entry_long, entry_short   (bool)   fill at NEXT bar open
        exit_long,  exit_short    (bool)   fill at signal bar CLOSE
        stop_long,  tp_long       (float)  bracket, NaN = no bracket
        stop_short, tp_short      (float)

Pipeline rules (enforced by run_backtest below):
  * signals are generated with information up to and including bar t only
  * entries fill at open of t+1 (realistic, no lookahead)
  * intrabar SL/TP conflicts resolve to the STOP (conservative)
  * costs: taker fees + slippage per side

Contents:
  Smart-money / liquidity .... 01 liq_fvg, 02 order_block, 03 breaker_block,
                                 04 pdh_sweep, 05 asian_sweep
  Trend / momentum ........... 06 ema_pullback, 07 adx_di_trend,
                                 08 donchian_turtle, 09 macd_momentum, 10 rsi2_connors
  Mean reversion / stats ..... 11 bb_mean_revert, 12 zscore_fade, 13 vwap_fade,
                                 14 ou_stationary_fade, 15 squeeze_rank_breakout
  Volatility ................. 16 ttm_squeeze, 17 atr_vol_breakout
  Machine learning ........... 18 logreg_walkforward, 19 hmm_regime_switch,
                                 20 gbm_walkforward

DISCLAIMER: demo metrics on synthetic data are smoke tests only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# =========================================================================== #
# Indicators
# =========================================================================== #
def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def adx(df: pd.DataFrame, n: int = 14) -> pd.DataFrame:
    h, l, c = df["high"], df["low"], df["close"]
    up = h.diff()
    dn = -l.diff()
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    trs = tr.ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / trs
    mdi = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / trs
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return pd.DataFrame({"adx": dx.ewm(alpha=1 / n, adjust=False).mean(),
                         "pdi": pdi, "mdi": mdi})


def zscore(s: pd.Series, n: int) -> pd.Series:
    m = s.rolling(n).mean()
    sd = s.rolling(n).std()
    return (s - m) / sd.replace(0, np.nan)


def _frame(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["entry_long", "entry_short", "exit_long", "exit_short",
            "stop_long", "tp_long", "stop_short", "tp_short"]
    sig = pd.DataFrame(False, index=df.index, columns=cols)
    for c in ["stop_long", "tp_long", "stop_short", "tp_short"]:
        sig[c] = np.nan
    return sig


def _levels_htf(df: pd.DataFrame, rule: str = "4h", lb: int = 2, rb: int = 2):
    """Confirmed swing levels on a higher timeframe. No lookahead: a pivot is
    only usable rb bars after it forms."""
    htf = df.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    out = []
    H, L, T = htf["high"].values, htf["low"].values, htf.index
    for i in range(lb, len(htf) - rb):
        if H[i] == H[i - lb:i + rb + 1].max():
            out.append((T[i + rb], H[i], "high"))
        if L[i] == L[i - lb:i + rb + 1].min():
            out.append((T[i + rb], L[i], "low"))
    return pd.DataFrame(out, columns=["confirmed_at", "level", "kind"]).set_index("confirmed_at").sort_index()


# =========================================================================== #
# 01 - 4H liquidity sweep + 15m FVG entry (ICT style)
# =========================================================================== #
def liq_fvg(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"pen_atr": 0.10, "buffer_atr": 0.25, "rr": 2.0, "valid": 12,
         "min_gap_atr": 0.15, **(p or {})}
    sig, a = _frame(df), atr(df)
    lv = _levels_htf(df)
    buf, pending_fvg = [], None     # pending_fvg: (dir, fvg_low, fvg_high, sweep_extreme)
    li = 0
    H, L, C, O = df["high"].values, df["low"].values, df["close"].values, df["open"].values
    for k in range(len(df)):
        t = df.index[k]
        while li < len(lv) and lv.index[li] <= t:
            r = lv.iloc[li]; buf.append({"px": r["level"], "kind": r["kind"], "used": False}); li += 1
        # bullish FVG formed at k-1: low[k-1] > high[k-3]
        if k >= 3 and pending_fvg is None:
            gap_lo, gap_hi = H[k - 3], L[k - 1]
            if gap_hi - gap_lo >= p["min_gap_atr"] * a.iloc[k]:
                # does an active swept-low context exist?
                for x in buf:
                    if x["kind"] == "low" and not x["used"] and k - 12 < len(df):
                        if L[k - 1] < x["px"] or L[k - 2] < x["px"]:
                            pending_fvg = (1, gap_lo, gap_hi, min(L[k - 1], L[k - 2], x["px"]))
                            x["used"] = True
                            break
                else:
                    pass
                for x in buf:
                    if x["kind"] == "high" and not x["used"]:
                        if H[k - 1] > x["px"] or H[k - 2] > x["px"]:
                            pending_fvg = (-1, gap_lo, gap_hi, max(H[k - 1], H[k - 2], x["px"]))
                            x["used"] = True
                            break
        # entry: price taps the FVG but closes back through its midpoint
        if pending_fvg is not None:
            d, glo, ghi, ext = pending_fvg
            mid = 0.5 * (glo + ghi)
            hit = L[k] <= ghi if d == 1 else H[k] >= glo
            if hit and ((d == 1 and C[k] > mid) or (d == -1 and C[k] < mid)):
                sl = ext - p["buffer_atr"] * a.iloc[k] if d == 1 else ext + p["buffer_atr"] * a.iloc[k]
                tp = C[k] + d * p["rr"] * abs(C[k] - sl)
                if d == 1:
                    sig.iloc[k, :3] = [True, False, False]
                    sig.loc[df.index[k], ["stop_long", "tp_long"]] = sl, tp
                else:
                    sig.iloc[k, 1:3] = [True, False]
                    sig.loc[df.index[k], ["stop_short", "tp_short"]] = sl, tp
                pending_fvg = None
            elif k > 0 and ((d == 1 and C[k] < glo) or (d == -1 and C[k] > ghi)):
                pending_fvg = None  # FVG mitigated without entry
    return sig


# =========================================================================== #
# 02 - Order block retest
# =========================================================================== #
def order_block(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"impulse_atr": 1.2, "lookback": 4, "valid": 30, "buffer_atr": 0.20,
         "rr": 2.0, **(p or {})}
    sig, a = _frame(df), atr(df)
    ob_long = ob_short = None   # (top, bottom, born)
    H, L, C, O = df["high"].values, df["low"].values, df["close"].values, df["open"].values
    for k in range(20, len(df)):
        body = abs(C[k] - O[k])
        if body >= p["impulse_atr"] * a.iloc[k]:
            if C[k] < O[k]:     # bearish impulse -> bearish OB = last up-candles before it
                seg = slice(k - p["lookback"], k)
                mask = C[seg] > O[seg]
                if mask.any():
                    ob_short = (H[k - p["lookback"]:k][mask].max(),
                                L[k - p["lookback"]:k][mask].min(), k)
            else:
                seg = slice(k - p["lookback"], k)
                mask = C[seg] < O[seg]
                if mask.any():
                    ob_long = (H[k - p["lookback"]:k][mask].max(),
                               L[k - p["lookback"]:k][mask].min(), k)
        for side, ob in ((1, ob_long), (-1, ob_short)):
            if ob is None or k - ob[2] > p["valid"]:
                continue
            top, bot, _ = ob
            inside = (L[k] <= top and H[k] >= bot)
            if not inside:
                continue
            if side == 1 and C[k] > O[k] and C[k] > 0.5 * (top + bot):
                sl = bot - p["buffer_atr"] * a.iloc[k]
                sig.loc[df.index[k], ["entry_long", "stop_long", "tp_long"]] = True, sl, C[k] + p["rr"] * (C[k] - sl)
                ob_long = None
            elif side == -1 and C[k] < O[k] and C[k] < 0.5 * (top + bot):
                sl = top + p["buffer_atr"] * a.iloc[k]
                sig.loc[df.index[k], ["entry_short", "stop_short", "tp_short"]] = True, sl, C[k] - p["rr"] * (sl - C[k])
                ob_short = None
    return sig


# =========================================================================== #
# 03 - Breaker block
# =========================================================================== #
def breaker_block(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"lb": 3, "rb": 3, "break_atr": 0.05, "buffer_atr": 0.25, "rr": 2.0,
         "valid": 40, **(p or {})}
    sig, a = _frame(df), atr(df)
    swings = []          # confirmed swing lows/highs
    H, L, C = df["high"].values, df["low"].values, df["close"].values
    for k in range(p["lb"] + p["rb"], len(df)):
        i = k - p["rb"]  # candidate pivot, confirmed now
        if H[i] == H[i - p["lb"]:i + p["rb"] + 1].max():
            swings.append({"px": H[i], "kind": "high", "broken": False, "conf": k})
        if L[i] == L[i - p["lb"]:i + p["rb"] + 1].min():
            swings.append({"px": L[i], "kind": "low", "broken": False, "conf": k})
        swings = [s for s in swings if k - s["conf"] <= p["valid"]]
        for s in swings:
            if s.get("dead"):
                continue
            if s["broken"]:
                # retest entry: wick back to level, close back on the break side
                if s["kind"] == "low" and H[k] >= s["px"] and C[k] < s["px"]:
                    sl = H[k] + p["buffer_atr"] * a.iloc[k]
                    sig.loc[df.index[k], ["entry_short", "stop_short", "tp_short"]] = True, sl, C[k] - p["rr"] * (sl - C[k])
                    s["dead"] = True
                elif s["kind"] == "high" and L[k] <= s["px"] and C[k] > s["px"]:
                    sl = L[k] - p["buffer_atr"] * a.iloc[k]
                    sig.loc[df.index[k], ["entry_long", "stop_long", "tp_long"]] = True, sl, C[k] + p["rr"] * (C[k] - sl)
                    s["dead"] = True
            else:
                pen = p["break_atr"] * a.iloc[k]
                if s["kind"] == "low" and C[k] < s["px"] - pen:
                    s["broken"] = True   # support failed -> becomes resistance
                elif s["kind"] == "high" and C[k] > s["px"] + pen:
                    s["broken"] = True
    return sig


# =========================================================================== #
# 04 - Previous day high / low sweep
# =========================================================================== #
def pdh_sweep(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"pen_atr": 0.05, "buffer_atr": 0.20, **(p or {})}
    sig, a = _frame(df), atr(df)
    d = df.resample("1D", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    pdh, pdl = d["high"].shift(1), d["low"].shift(1)
    lvl = pd.concat([pdh.rename("h"), pdl.rename("l")], axis=1).reindex(
        df.index, method="ffill")
    H, L, C = df["high"].values, df["low"].values, df["close"].values
    h_, l_ = lvl["h"].values, lvl["l"].values
    for k in range(len(df)):
        if np.isnan(h_[k]):
            continue
        if H[k] > h_[k] + p["pen_atr"] * a.iloc[k] and C[k] < h_[k] and H[k] > l_[k]:
            sl = H[k] + p["buffer_atr"] * a.iloc[k]
            sig.loc[df.index[k], ["entry_short", "stop_short", "tp_short"]] = True, sl, l_[k]
        elif L[k] < l_[k] - p["pen_atr"] * a.iloc[k] and C[k] > l_[k] and L[k] < h_[k]:
            sl = L[k] - p["buffer_atr"] * a.iloc[k]
            sig.loc[df.index[k], ["entry_long", "stop_long", "tp_long"]] = True, sl, h_[k]
    return sig


# =========================================================================== #
# 05 - Asian range sweep (London killzone)
# =========================================================================== #
def asian_sweep(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"pen_atr": 0.03, "buffer_atr": 0.20, **(p or {})}
    sig, a = _frame(df), atr(df)
    H, L, C = df["high"].values, df["low"].values, df["close"].values
    hrs = df.index.hour + df.index.minute / 60
    rng = {}   # date -> (asian_high, asian_low)
    cur = None
    for k in range(len(df)):
        day = df.index[k].date()
        if hrs[k] < 7:                       # build Asian range 00-07 UTC
            if day not in rng:
                rng[day] = [H[k], L[k]]
                cur = day
            else:
                rng[day][0] = max(rng[day][0], H[k])
                rng[day][1] = min(rng[day][1], L[k])
            continue
        if cur is None or day not in rng:
            continue
        ah, al = rng[day]
        if 7 <= hrs[k] < 12 and ah > al:     # London window only
            if H[k] > ah + p["pen_atr"] * a.iloc[k] and C[k] < ah:
                sl = H[k] + p["buffer_atr"] * a.iloc[k]
                sig.loc[df.index[k], ["entry_short", "stop_short", "tp_short"]] = True, sl, al
            elif L[k] < al - p["pen_atr"] * a.iloc[k] and C[k] > al:
                sl = L[k] - p["buffer_atr"] * a.iloc[k]
                sig.loc[df.index[k], ["entry_long", "stop_long", "tp_long"]] = True, sl, ah
    return sig


# =========================================================================== #
# 06 - EMA pullback trend continuation
# =========================================================================== #
def ema_pullback(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"fast": 21, "slow": 55, "regime": 200, "rr": 2.5, "rsi_mid": 45,
         "sl_swing": 5, "buffer_atr": 0.25, **(p or {})}
    sig, a = _frame(df), atr(df)
    ef, es_, er = ema(df["close"], p["fast"]), ema(df["close"], p["slow"]), ema(df["close"], p["regime"])
    r = rsi(df["close"])
    C, L = df["close"].values, df["low"].values
    trend = 0
    for k in range(p["regime"], len(df)):
        if C[k] > er.iloc[k] and ef.iloc[k] > es_.iloc[k]:
            trend = 1
        elif C[k] < er.iloc[k] and ef.iloc[k] < es_.iloc[k]:
            trend = -1
        else:
            trend = 0
        touched = L[k] <= ef.iloc[k] * 1.001 if trend == 1 else df["high"].values[k] >= ef.iloc[k] * 0.999
        if trend == 1 and touched and r.iloc[k] > p["rsi_mid"] and r.iloc[k - 1] <= p["rsi_mid"]:
            sl = L[k - p["sl_swing"]:k + 1].min() - p["buffer_atr"] * a.iloc[k]
            sig.loc[df.index[k], ["entry_long", "stop_long", "tp_long"]] = True, sl, C[k] + p["rr"] * (C[k] - sl)
            sig.loc[df.index[k], "exit_long"] = C[k] < es_.iloc[k]
        elif trend == -1 and touched and r.iloc[k] < 100 - p["rsi_mid"] and r.iloc[k - 1] >= 100 - p["rsi_mid"]:
            sl = df["high"].values[k - p["sl_swing"]:k + 1].max() + p["buffer_atr"] * a.iloc[k]
            sig.loc[df.index[k], ["entry_short", "stop_short", "tp_short"]] = True, sl, C[k] - p["rr"] * (sl - C[k])
            sig.loc[df.index[k], "exit_short"] = C[k] > es_.iloc[k]
    return sig


# =========================================================================== #
# 07 - ADX / DMI trend with pullback trigger
# =========================================================================== #
def adx_di_trend(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"adx_in": 22, "adx_out": 17, "sl_atr": 2.0, **(p or {})}
    sig, a = _frame(df), atr(df)
    d = adx(df)
    cross_up = (d["pdi"] > d["mdi"]) & (d["pdi"].shift(1) <= d["mdi"].shift(1))
    cross_dn = (d["pdi"] < d["mdi"]) & (d["pdi"].shift(1) >= d["mdi"].shift(1))
    long_e = cross_up & (d["adx"] > p["adx_in"])
    short_e = cross_dn & (d["adx"] > p["adx_in"])
    sig.loc[long_e, "entry_long"] = True
    sig.loc[short_e, "entry_short"] = True
    sl_l = df["close"] - p["sl_atr"] * a
    sl_s = df["close"] + p["sl_atr"] * a
    sig.loc[long_e, "stop_long"] = sl_l[long_e]
    sig.loc[short_e, "stop_short"] = sl_s[short_e]
    flat = d["adx"] < p["adx_out"]
    sig.loc[flat, ["exit_long", "exit_short"]] = True
    sig.loc[cross_dn, "exit_long"] = True
    sig.loc[cross_up, "exit_short"] = True
    return sig


# =========================================================================== #
# 08 - Donchian breakout (Turtle-style)
# =========================================================================== #
def donchian_turtle(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"entry_n": 20, "exit_n": 10, "regime": 100, "sl_atr": 2.0, **(p or {})}
    sig, a = _frame(df), atr(df)
    up = df["high"].rolling(p["entry_n"]).max().shift(1)
    dn = df["low"].rolling(p["entry_n"]).min().shift(1)
    ex_l = df["low"].rolling(p["exit_n"]).min().shift(1)
    ex_s = df["high"].rolling(p["exit_n"]).max().shift(1)
    er = ema(df["close"], p["regime"])
    long_e = (df["close"] > up) & (df["close"] > er)
    short_e = (df["close"] < dn) & (df["close"] < er)
    sig.loc[long_e, "entry_long"] = True
    sig.loc[short_e, "entry_short"] = True
    sig.loc[long_e, "stop_long"] = (df["close"] - p["sl_atr"] * a)[long_e]
    sig.loc[short_e, "stop_short"] = (df["close"] + p["sl_atr"] * a)[short_e]
    sig.loc[df["close"] < ex_l, "exit_long"] = True
    sig.loc[df["close"] > ex_s, "exit_short"] = True
    return sig


# =========================================================================== #
# 09 - MACD momentum with regime filter
# =========================================================================== #
def macd_momentum(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"fast": 12, "slow": 26, "sig": 9, "regime": 200, "sl_atr": 1.8, **(p or {})}
    sig, a = _frame(df), atr(df)
    ml = ema(df["close"], p["fast"]) - ema(df["close"], p["slow"])
    ms = ml.ewm(span=p["sig"], adjust=False).mean()
    hist = ml - ms
    er = ema(df["close"], p["regime"])
    rising = (hist > hist.shift(1)) & (hist.shift(1) > hist.shift(2))
    falling = (hist < hist.shift(1)) & (hist.shift(1) < hist.shift(2))
    long_e = (ml > ms) & rising & (df["close"] > er)
    short_e = (ml < ms) & falling & (df["close"] < er)
    sig.loc[long_e, "entry_long"] = True
    sig.loc[short_e, "entry_short"] = True
    sig.loc[long_e, "stop_long"] = (df["close"] - p["sl_atr"] * a)[long_e]
    sig.loc[short_e, "stop_short"] = (df["close"] + p["sl_atr"] * a)[short_e]
    sig.loc[(ml < ms) & (ml.shift(1) >= ms.shift(1)), "exit_long"] = True
    sig.loc[(ml > ms) & (ml.shift(1) <= ms.shift(1)), "exit_short"] = True
    return sig


# =========================================================================== #
# 10 - RSI-2 mean reversion (Connors-style)
# =========================================================================== #
def rsi2_connors(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"rsi_n": 2, "regime": 200, "buy": 10, "sell": 90, "exit_hi": 70,
         "exit_lo": 30, "max_hold": 5, **(p or {})}
    sig = _frame(df)
    r2 = rsi(df["close"], p["rsi_n"])
    reg = sma(df["close"], p["regime"])
    sig.loc[(df["close"] > reg) & (r2 < p["buy"]), "entry_long"] = True
    sig.loc[(df["close"] < reg) & (r2 > p["sell"]), "entry_short"] = True
    sig.loc[(r2 > p["exit_hi"]), "exit_long"] = True
    sig.loc[(r2 < p["exit_lo"]), "exit_short"] = True
    sig.attrs["max_hold"] = p["max_hold"]
    return sig


# =========================================================================== #
# 11 - Bollinger mean reversion
# =========================================================================== #
def bb_mean_revert(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"n": 20, "k": 2.0, "exit_z": 0.0, "stop_k": 3.5, **(p or {})}
    sig = _frame(df)
    m = sma(df["close"], p["n"])
    sd = df["close"].rolling(p["n"]).std()
    z = (df["close"] - m) / sd.replace(0, np.nan)
    long_e = (z < -p["k"]) & (z.shift(1) >= -p["k"])
    short_e = (z > p["k"]) & (z.shift(1) <= p["k"])
    sig.loc[long_e, "entry_long"] = True
    sig.loc[short_e, "entry_short"] = True
    sig.loc[long_e, "stop_long"] = (m - p["stop_k"] * sd)[long_e]
    sig.loc[short_e, "stop_short"] = (m + p["stop_k"] * sd)[short_e]
    sig.loc[(z > p["exit_z"]) & (z.shift(1) <= p["exit_z"]), "exit_long"] = True
    sig.loc[(z < p["exit_z"]) & (z.shift(1) >= p["exit_z"]), "exit_short"] = True
    return sig


# =========================================================================== #
# 12 - Rolling z-score fade
# =========================================================================== #
def zscore_fade(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"n": 100, "z_in": 2.0, "z_out": 0.0, "z_stop": 3.5, "max_hold": 48, **(p or {})}
    sig = _frame(df)
    z = zscore(df["close"], p["n"])
    long_e = (z < -p["z_in"]) & (z.shift(1) >= -p["z_in"])
    short_e = (z > p["z_in"]) & (z.shift(1) <= p["z_in"])
    sig.loc[long_e, "entry_long"] = True
    sig.loc[short_e, "entry_short"] = True
    m = df["close"].rolling(p["n"]).mean()
    sd = df["close"].rolling(p["n"]).std()
    sig.loc[long_e, "stop_long"] = (m - p["z_stop"] * sd)[long_e]
    sig.loc[short_e, "stop_short"] = (m + p["z_stop"] * sd)[short_e]
    sig.loc[(z > p["z_out"]) & (z.shift(1) <= p["z_out"]), "exit_long"] = True
    sig.loc[(z < p["z_out"]) & (z.shift(1) >= p["z_out"]), "exit_short"] = True
    sig.attrs["max_hold"] = p["max_hold"]
    return sig


# =========================================================================== #
# 13 - Intraday VWAP fade
# =========================================================================== #
def vwap_fade(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"z_in": 2.0, "z_win": 30, "k_stop": 3.5, **(p or {})}
    sig = _frame(df)
    tp = (df["high"] + df["low"] + df["close"]) / 3
    for _, day in df.groupby(df.index.date):
        v = df.loc[day.index, "volume"].values
        pv = (tp[day.index] * v).cumsum() / np.cumsum(v)
        dev = tp[day.index] - pd.Series(pv, index=day.index)
        sd = dev.rolling(p["z_win"], min_periods=5).std()
        z = dev / sd.replace(0, np.nan)
        o, c = day["open"].values, day["close"].values
        lo, hi = day["low"].values, day["high"].values
        sl = pd.Series(pv, index=day.index) - p["k_stop"] * sd
        ss = pd.Series(pv, index=day.index) + p["k_stop"] * sd
        le = (z < -p["z_in"]) & (c > o)           # touched lower band, rejected up
        se = (z > p["z_in"]) & (c < o)
        sig.loc[day.index[le], "entry_long"] = True
        sig.loc[day.index[se], "entry_short"] = True
        sig.loc[day.index[le], "stop_long"] = sl[le]
        sig.loc[day.index[se], "stop_short"] = ss[se]
        back = (dev > 0) & (dev.shift(1) <= 0)
        back2 = (dev < 0) & (dev.shift(1) >= 0)
        sig.loc[day.index[back], "exit_long"] = True
        sig.loc[day.index[back2], "exit_short"] = True
    return sig


# =========================================================================== #
# 14 - Ornstein-Uhlenbeck half-life gated fade
# =========================================================================== #
def ou_stationary_fade(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"detrend": 50, "win": 200, "hl_lo": 3, "hl_hi": 100,
         "z_in": 2.0, "z_out": 0.0, "z_stop": 4.0, **(p or {})}
    sig = _frame(df)
    x = df["close"] - ema(df["close"], p["detrend"])
    phi = x.rolling(p["win"]).corr(x.shift(1)).clip(0.01, 0.995)
    half_life = -np.log(2) / np.log(phi)
    valid = (half_life > p["hl_lo"]) & (half_life < p["hl_hi"])
    sd = x.rolling(p["win"]).std()
    z = x / sd.replace(0, np.nan)
    long_e = valid & (z < -p["z_in"]) & (z.shift(1) >= -p["z_in"])
    short_e = valid & (z > p["z_in"]) & (z.shift(1) <= p["z_in"])
    sig.loc[long_e, "entry_long"] = True
    sig.loc[short_e, "entry_short"] = True
    # stop expressed in PRICE space: z = (close - ema)/sd -> px_stop = close -/+ (z_stop -+ z) * sd
    sig.loc[long_e, "stop_long"] = (df["close"] - (z + p["z_stop"]) * sd)[long_e]
    sig.loc[short_e, "stop_short"] = (df["close"] + (p["z_stop"] - z) * sd)[short_e]
    sig.loc[(z > p["z_out"]) & (z.shift(1) <= p["z_out"]), "exit_long"] = True
    sig.loc[(z < p["z_out"]) & (z.shift(1) >= p["z_out"]), "exit_short"] = True
    return sig


# =========================================================================== #
# 15 - Volatility-compression rank breakout
# =========================================================================== #
def squeeze_rank_breakout(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"bb_n": 20, "k": 2.0, "rank_n": 200, "arm": 0.15, "n": 20,
         "sl_atr": 1.8, "max_hold": 24, **(p or {})}
    sig, a = _frame(df), atr(df)
    m = sma(df["close"], p["bb_n"])
    sd = df["close"].rolling(p["bb_n"]).std()
    width = 2 * p["k"] * sd / m
    rank = width.rolling(p["rank_n"]).apply(lambda w: (w[-1] > w).mean(), raw=True)
    hh = df["high"].rolling(p["n"]).max().shift(1)
    ll = df["low"].rolling(p["n"]).min().shift(1)
    roc = df["close"].pct_change(10)
    armed = rank < p["arm"]
    long_e = armed.shift(1, fill_value=False) & (df["close"] > hh) & (roc > 0)
    short_e = armed.shift(1, fill_value=False) & (df["close"] < ll) & (roc < 0)
    sig.loc[long_e, "entry_long"] = True
    sig.loc[short_e, "entry_short"] = True
    sig.loc[long_e, "stop_long"] = (df["close"] - p["sl_atr"] * a)[long_e]
    sig.loc[short_e, "stop_short"] = (df["close"] + p["sl_atr"] * a)[short_e]
    sig.loc[rank > 0.6, ["exit_long", "exit_short"]] = True
    sig.attrs["max_hold"] = p["max_hold"]
    return sig


# =========================================================================== #
# 16 - TTM squeeze momentum
# =========================================================================== #
def ttm_squeeze(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"n": 20, "bb_k": 2.0, "kc_k": 1.5, "mom_n": 20, "sl_atr": 2.0, **(p or {})}
    sig, a = _frame(df), atr(df)
    m = sma(df["close"], p["n"])
    sd = df["close"].rolling(p["n"]).std()
    up_bb, lo_bb = m + p["bb_k"] * sd, m - p["bb_k"] * sd
    rng = (df["high"] - df["low"]).rolling(p["n"]).mean()
    up_kc, lo_kc = m + p["kc_k"] * rng, m - p["kc_k"] * rng
    squeezed = (up_bb < up_kc) & (lo_bb > lo_kc)
    hl2 = (df["high"] + df["low"] + df["close"]) / 3
    mom = (hl2 - (hl2.rolling(p["mom_n"]).max() + hl2.rolling(p["mom_n"]).min()) / 2)
    mom_prev = mom.shift(1)
    long_e = squeezed.shift(1, fill_value=False) & (mom > 0) & (mom_prev <= 0)
    short_e = squeezed.shift(1, fill_value=False) & (mom < 0) & (mom_prev >= 0)
    sig.loc[long_e, "entry_long"] = True
    sig.loc[short_e, "entry_short"] = True
    sig.loc[long_e, "stop_long"] = (df["close"] - p["sl_atr"] * a)[long_e]
    sig.loc[short_e, "stop_short"] = (df["close"] + p["sl_atr"] * a)[short_e]
    sig.loc[(mom < 0) & (mom_prev >= 0), "exit_long"] = True
    sig.loc[(mom > 0) & (mom_prev <= 0), "exit_short"] = True
    return sig


# =========================================================================== #
# 17 - ATR expansion breakout (chandelier-lite trailing)
# =========================================================================== #
def atr_vol_breakout(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"n": 96, "atr_n": 14, "trail_atr": 2.5, "min_atr_rank": 0.5, **(p or {})}
    sig, a = _frame(df), atr(df, p["atr_n"])
    hh = df["high"].rolling(p["n"]).max().shift(1)
    ll = df["low"].rolling(p["n"]).min().shift(1)
    a_rank = a.rolling(300).apply(lambda w: (w[-1] > w).mean(), raw=True)
    expanding = (a > a.shift(1)) & (a.shift(1) > a.shift(2))
    long_e = (df["close"] > hh) & expanding & (a_rank > p["min_atr_rank"])
    short_e = (df["close"] < ll) & expanding & (a_rank > p["min_atr_rank"])
    sig.loc[long_e, "entry_long"] = True
    sig.loc[short_e, "entry_short"] = True
    trail_l = df["high"].rolling(48).max() - p["trail_atr"] * a
    trail_s = df["low"].rolling(48).min() + p["trail_atr"] * a
    sig.loc[long_e, "stop_long"] = trail_l[long_e]
    sig.loc[short_e, "stop_short"] = trail_s[short_e]
    sig.loc[df["close"] < ema(df["close"], 21), "exit_long"] = True
    sig.loc[df["close"] > ema(df["close"], 21), "exit_short"] = True
    return sig


# =========================================================================== #
# Walk-forward ML scaffold
# =========================================================================== #
def _features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    c = df["close"]
    r1 = c.pct_change(1)
    X = pd.DataFrame({
        "r1": r1, "r2": c.pct_change(2), "r3": c.pct_change(3),
        "r5": c.pct_change(5), "r8": c.pct_change(8), "r13": c.pct_change(13),
        "rsi": rsi(c) / 100 - 0.5,
        "atr_pct": atr(df) / c,
        "bb_z": zscore(c, 20),
        "mom20": c.pct_change(20),
        "vol20": r1.rolling(20).std(),
        "hour_sin": np.sin(2 * np.pi * (df.index.hour + df.index.minute / 60) / 24),
        "hour_cos": np.cos(2 * np.pi * (df.index.hour + df.index.minute / 60) / 24),
    }, index=df.index)
    y = (c.shift(-4) / c - 1 > 0).astype(float)   # 1-hour-ahead direction
    return X, y


class _LogReg:
    """Tiny L2 logistic regression (numpy). Deterministic, no sklearn needed."""
    def __init__(self, lr=0.5, iters=250, lam=1.0):
        self.lr, self.iters, self.lam = lr, iters, lam

    def fit(self, X, y):
        mu, sd = X.mean(0), X.std(0) + 1e-12
        Xs = (X - mu) / sd
        w = np.zeros(Xs.shape[1])
        for _ in range(self.iters):
            p = 1 / (1 + np.exp(-Xs @ w))
            g = Xs.T @ (p - y) / len(y) + self.lam * w / len(y)
            w -= self.lr * g
        self.w, self.mu, self.sd = w, mu, sd
        return self

    def predict_proba(self, X):
        Xs = (X - self.mu) / self.sd
        p = 1 / (1 + np.exp(-Xs @ self.w))
        return np.c_[1 - p, p]


def _walkforward(df, model_factory, train=1500, step=96, thr_long=0.58,
                 thr_short=0.42, max_hold=8, sl_atr=1.5):
    X, y = _features(df)
    a = atr(df)
    sig = _frame(df)
    cols = X.columns
    idx = np.where(X.notna().all(1).values)[0]
    Xv, yv = X.values, y.values
    start = idx[0]
    for t0 in range(start + train, len(df) - 8, step):
        tr = np.arange(t0 - train, t0)
        m = model_factory().fit(Xv[tr], yv[tr])
        hi = min(t0 + step, len(df) - 4)
        P = m.predict_proba(Xv[t0:hi])
        for j, k in enumerate(range(t0, hi)):
            p = P[j, 1]
            if p > thr_long:
                sl = df["close"].values[k] - sl_atr * a.values[k]
                sig.iloc[k, 0] = True
                sig.loc[df.index[k], ["stop_long", "tp_long"]] = sl, np.nan
            elif p < thr_short:
                sl = df["close"].values[k] + sl_atr * a.values[k]
                sig.iloc[k, 1] = True
                sig.loc[df.index[k], ["stop_short", "tp_short"]] = sl, np.nan
            if 0.45 < p < 0.55:
                sig.iloc[k, 2] = True
                sig.iloc[k, 3] = True
    sig.attrs["max_hold"] = max_hold
    return sig


def logreg_walkforward(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    return _walkforward(df, _LogReg)


def gbm_walkforward(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    try:
        from sklearn.ensemble import HistGradientBoostingClassifier
        class _F:
            def fit(self, X, y):
                self.m = HistGradientBoostingClassifier(max_iter=150, learning_rate=0.08,
                                                        max_depth=3, random_state=0)
                self.m.fit(X, y)
                return self
            def predict_proba(self, X):
                return self.m.predict_proba(X)
        return _walkforward(df, _F, thr_long=0.60, thr_short=0.40, sl_atr=1.2)
    except Exception:
        return _walkforward(df, _LogReg)


# =========================================================================== #
# 19 - 2-state HMM regime switch (trend state -> trend system, range state -> fade)
# =========================================================================== #
def _hmm2_fit(r: np.ndarray, iters: int = 12, seed: int = 0):
    rng = np.random.default_rng(seed)
    mu = r.mean() + rng.normal(0, r.std() / 4, 2)
    var = np.clip(r.var() * np.array([0.5, 2.0]), 1e-12, None)
    A = np.array([[0.95, 0.05], [0.05, 0.95]])
    pi = np.array([0.5, 0.5])
    n = len(r)
    for _ in range(iters):
        B = np.exp(-0.5 * ((r[:, None] - mu[None, :]) ** 2) / var[None, :]) / np.sqrt(2 * np.pi * var[None, :])
        alpha = np.empty((n, 2)); c = np.empty(n)
        alpha[0] = pi * B[0]; c[0] = alpha[0].sum(); alpha[0] /= c[0]
        for t in range(1, n):
            alpha[t] = (alpha[t - 1] @ A) * B[t]
            c[t] = alpha[t].sum(); alpha[t] /= c[t]
        beta = np.ones((n, 2))
        for t in range(n - 2, -1, -1):
            beta[t] = (A @ (B[t + 1] * beta[t + 1])) / c[t + 1]
        gam = alpha * beta
        gam /= gam.sum(1, keepdims=True)
        xi_sum = np.zeros((2, 2))
        for t in range(n - 1):
            x = np.outer(alpha[t], B[t + 1] * beta[t + 1]) * A
            xi_sum += x / x.sum()
        A = xi_sum / xi_sum.sum(1, keepdims=True)
        pi = gam[0]
        mu = (gam * r[:, None]).sum(0) / gam.sum(0)
        var = (gam * (r[:, None] - mu[None, :]) ** 2).sum(0) / gam.sum(0)
    trend_state = int(np.argmax(np.abs(mu) / np.sqrt(var)))
    B = np.exp(-0.5 * ((r[:, None] - mu[None, :]) ** 2) / var[None, :]) / np.sqrt(2 * np.pi * var[None, :])
    alpha = pi * B[0]
    alpha = alpha / alpha.sum()
    for tt in range(1, n):
        alpha = (alpha @ A) * B[tt]
        alpha = alpha / alpha.sum()
    return mu, var, A, alpha, trend_state


def hmm_regime_switch(df: pd.DataFrame, p: dict | None = None) -> pd.DataFrame:
    p = {"train": 600, "step": 192, "trend_prob": 0.7, "mr_prob": 0.7,
         "z_n": 50, "z_in": 2.0, "z_out": 0.2, "adx_n": 14, "sl_atr": 2.0, **(p or {})}
    sig, a = _frame(df), atr(df)
    r = df["close"].pct_change().values
    d = adx(df, p["adx_n"])
    z = zscore(df["close"], p["z_n"]).values
    for t0 in range(p["train"], len(df) - 4, p["step"]):
        w = slice(t0 - p["train"], t0)
        try:
            _, _, _, probs, ts = _hmm2_fit(r[w])
        except Exception:
            continue
        hi = min(t0 + p["step"], len(df) - 1)
        for k in range(t0, hi):
            if probs[ts] > p["trend_prob"]:              # TREND regime
                if d["pdi"].values[k] > d["mdi"].values[k] and d["adx"].values[k] > 20:
                    if not sig["entry_long"].values[max(0, k - 1)]:
                        sl = df["close"].values[k] - p["sl_atr"] * a.values[k]
                        sig.iloc[k, 0] = True
                        sig.loc[df.index[k], ["stop_long", "tp_long"]] = sl, np.nan
                elif d["mdi"].values[k] > d["pdi"].values[k] and d["adx"].values[k] > 20:
                    if not sig["entry_short"].values[max(0, k - 1)]:
                        sl = df["close"].values[k] + p["sl_atr"] * a.values[k]
                        sig.iloc[k, 1] = True
                        sig.loc[df.index[k], ["stop_short", "tp_short"]] = sl, np.nan
                if d["adx"].values[k] < 15:
                    sig.iloc[k, 2] = True; sig.iloc[k, 3] = True
            elif probs[1 - ts] > p["mr_prob"]:           # RANGE regime -> fade
                if z[k] < -p["z_in"]:
                    sl = df["close"].values[k] - p["sl_atr"] * a.values[k]
                    sig.iloc[k, 0] = True
                    sig.loc[df.index[k], ["stop_long", "tp_long"]] = sl, np.nan
                elif z[k] > p["z_in"]:
                    sl = df["close"].values[k] + p["sl_atr"] * a.values[k]
                    sig.iloc[k, 1] = True
                    sig.loc[df.index[k], ["stop_short", "tp_short"]] = sl, np.nan
                if abs(z[k]) < p["z_out"]:
                    sig.iloc[k, 2] = True; sig.iloc[k, 3] = True
    return sig


# =========================================================================== #
# Registry + generic event-loop backtest
# =========================================================================== #
STRATEGIES = {
    "01_liq_fvg": liq_fvg, "02_order_block": order_block,
    "03_breaker_block": breaker_block, "04_pdh_sweep": pdh_sweep,
    "05_asian_sweep": asian_sweep, "06_ema_pullback": ema_pullback,
    "07_adx_di_trend": adx_di_trend, "08_donchian_turtle": donchian_turtle,
    "09_macd_momentum": macd_momentum, "10_rsi2_connors": rsi2_connors,
    "11_bb_mean_revert": bb_mean_revert, "12_zscore_fade": zscore_fade,
    "13_vwap_fade": vwap_fade, "14_ou_stationary_fade": ou_stationary_fade,
    "15_squeeze_rank_breakout": squeeze_rank_breakout, "16_ttm_squeeze": ttm_squeeze,
    "17_atr_vol_breakout": atr_vol_breakout, "18_logreg_walkforward": logreg_walkforward,
    "19_hmm_regime_switch": hmm_regime_switch, "20_gbm_walkforward": gbm_walkforward,
}


def run_backtest(df: pd.DataFrame, sig: pd.DataFrame, fees_bps: float = 5.0,
                 slippage_bps: float = 2.0) -> tuple[pd.DataFrame, pd.Series, dict]:
    cost = (fees_bps + slippage_bps) / 1e4
    max_hold = sig.attrs.get("max_hold", 192)
    o = df["open"].values; h = df["high"].values; l = df["low"].values
    c = df["close"].values; idx = df.index
    el = sig["entry_long"].values; es_ = sig["entry_short"].values
    xl = sig["exit_long"].values; xs = sig["exit_short"].values
    sl_l = sig["stop_long"].values; tp_l = sig["tp_long"].values
    sl_s = sig["stop_short"].values; tp_s = sig["tp_short"].values
    trades, pending, pos = [], None, None
    cash, eq, eqt = 1.0, [1.0], [idx[0]]
    for k in range(len(df)):
        if pending is not None and pos is None:
            side, sl, tp = pending
            fill = o[k] * (1 + cost if side == 1 else 1 - cost)
            pos = dict(dir=side, sl=sl, tp=tp, entry=fill, t=k, unit=cash / fill)
            pending = None
        if pos is not None:
            d = pos["dir"]
            sl = pos["sl"]; tp = pos["tp"]
            hit_sl = (not np.isnan(sl)) and (l[k] <= sl if d == 1 else h[k] >= sl)
            hit_tp = (not np.isnan(tp)) and (h[k] >= tp if d == 1 else l[k] <= tp)
            sig_exit = xl[k] if d == 1 else xs[k]
            if hit_sl or hit_tp or sig_exit or (k - pos["t"] >= max_hold):
                if hit_sl and hit_tp:
                    px = sl
                elif hit_sl:
                    px = sl
                elif hit_tp:
                    px = tp
                else:
                    px = c[k]
                px *= (1 - cost if d == 1 else 1 + cost)
                pnl = (px - pos["entry"]) * d * pos["unit"]
                cash += pnl
                trades.append(dict(entry_time=idx[pos["t"]], exit_time=idx[k],
                                   dir="long" if d == 1 else "short",
                                   entry=pos["entry"], exit=px, pnl=pnl, win=pnl > 0))
                pos = None
        if pos is None and pending is None and k + 1 < len(df):
            if el[k]:
                pending = (1, sl_l[k], tp_l[k])
            elif es_[k]:
                pending = (-1, sl_s[k], tp_s[k])
        eq.append(cash); eqt.append(idx[k])
    tr = pd.DataFrame(trades)
    eqs = pd.Series(eq[1:], index=eqt[1:])
    w = tr[tr["win"]]["pnl"].sum() if len(tr) else 0.0
    lo = -tr[~tr["win"]]["pnl"].sum() if len(tr) else 0.0
    m = dict(trades=len(tr),
             win_rate=float(tr["win"].mean()) if len(tr) else np.nan,
             profit_factor=float(w / lo) if lo > 0 else np.inf,
             total_return=float(eqs.iloc[-1] - 1) if len(eqs) else 0.0,
             max_drawdown=float((eqs / eqs.cummax() - 1).min()) if len(eqs) else np.nan)
    return tr, eqs, m


def run_all(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, fn in STRATEGIES.items():
        try:
            sig = fn(df)
            _, _, m = run_backtest(df, sig)
        except Exception as e:  # keep the report alive if one strategy fails
            m = dict(trades=0, win_rate=np.nan, profit_factor=np.nan,
                     total_return=0.0, max_drawdown=np.nan)
            m["error"] = str(e)[:60]
        rows.append(dict(strategy=name, **m))
    rep = pd.DataFrame(rows).set_index("strategy")
    return rep.sort_values("profit_factor", ascending=False)


if __name__ == "__main__":
    # regime-switching synthetic series: trend segments + OU-ish chop
    rng = np.random.default_rng(11)
    n = 96 * 100
    t = pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC")
    regime = np.repeat(rng.choice([-1, 0, 1], 13), int(np.ceil(n / 13)))[:n]
    trend = np.cumsum(regime * 0.00025)
    ar = np.zeros(n)
    e = rng.normal(0, 0.0012, n)
    for i in range(1, n):
        ar[i] = 0.90 * ar[i - 1] + e[i]
    close = 40000 * np.exp(trend + ar)
    o = np.roll(close, 1); o[0] = close[0]
    df = pd.DataFrame({
        "open": o,
        "high": np.maximum(o, close) * (1 + abs(rng.normal(0, 0.0007, n))),
        "low": np.minimum(o, close) * (1 - abs(rng.normal(0, 0.0007, n))),
        "close": close, "volume": rng.uniform(10, 200, n)}, index=t)
    pd.set_option("display.width", 160)
    print(run_all(df).round(3))
