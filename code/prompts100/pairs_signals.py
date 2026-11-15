#!/usr/bin/env python
r"""
pairs_signals.py — the SIGNAL construction of the pack's pair and basket
prompts (ids 81-90), cut out of the pack's own engine and kept VERBATIM in
the part that matters: the indicator maths and the entry/exit rules.

Provenance: code/prompts100/backtest100_pairs_engine.py (copied verbatim and
pinned by sha256 in code/prompts100/MANIFEST.json). The pack's functions
compute their signals AND run their own backtest in one go; here the signal
arrays are returned so the REPO's book can execute them.

WHAT IS PORTED VERBATIM
------------------------
- the spread construction (log ratio, rolling hedge ratio, Kalman beta,
  cointegration residual) and every indicator on it
- the entry and exit rules (the z-score thresholds, the stop levels, the
  number of standard deviations)
- the basket's ranking, its rebalance cadence and its leg weights

WHAT IS NOT PORTED (it is the repo's business)
-----------------------------------------------
- the execution: fills, stops, sizing, costs, funding and the ledger live in
  code/p100_screen_engine.py (the repo's conventions)
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "..", "prompts100")
if PACK not in sys.path:
    sys.path.insert(0, PACK)

import backtest100_pairs_engine as PK     # noqa: E402  (verbatim copy)

BARS_PER_YEAR = {"1h": 8760.0, "15m": 35040.0, "5m": 105120.0}


# ═════════════════════════════════════════════════════════════════════════
# the SPREAD pairs (81, 82, 85, 86, 89)
# ═════════════════════════════════════════════════════════════════════════
def pair_signal(sid: int) -> dict:
    """The signal arrays of a spread pair: the spread's close and open
    series, the desired side per bar, the stop level per bar and the hedge
    ratio (scalar or per bar)."""
    if sid == 81:                                  # SOL/ETH z-score
        a = PK.load_klines("SOLUSDT", "1h")
        b = PK.load_klines("ETHUSDT", "1h")
        m = PK.align(a, b)
        s = np.log(m["close_a"]) - np.log(m["close_b"])
        z = PK.zscore(s, 100)
        sd = s.rolling(100).std().values
        mean = s.rolling(100).mean().values
        zv = z.values
        side = np.zeros(len(m))
        stop_s = np.full(len(m), np.nan)
        in_pos = 0
        for j in range(len(m)):
            if not np.isfinite(zv[j]):
                continue
            if in_pos == 0:
                if zv[j] < -2.0:
                    in_pos = 1
                    side[j] = 1
                    stop_s[j] = mean[j] - 4.0 * sd[j]
            elif zv[j] > 0.0:
                in_pos = 0
        s_open = np.log(m["open_a"]) - np.log(m["open_b"])
        return dict(legs=("SOLUSDT", "ETHUSDT"), tf="1h",
                    s=np.asarray(s.values, float),
                    s_open=np.asarray(s_open.values, float),
                    side=side, stop_s=stop_s, beta=1.0,
                    ts=list(m["timestamp"].astype(str)),
                    bh=float((m["close_a"].iloc[-1] / m["close_a"].iloc[0] - 1)
                             * 100))

    if sid == 82:                                  # BTC/ETH z-score
        a = PK.load_klines("BTCUSDT", "1h")
        b = PK.load_klines("ETHUSDT", "1h")
        m = PK.align(a, b)
        s = np.log(m["close_a"]) - np.log(m["close_b"])
        z = PK.zscore(s, 100)
        sd = s.rolling(100).std().values
        mean = s.rolling(100).mean().values
        zv = z.values
        side = np.zeros(len(m))
        stop_s = np.full(len(m), np.nan)
        in_pos = 0
        for j in range(len(m)):
            if not np.isfinite(zv[j]):
                continue
            if in_pos == 0 and abs(zv[j]) > 2.0:
                in_pos = 1 if zv[j] < 0 else -1
                side[j] = in_pos
                stop_s[j] = mean[j] + in_pos * (-3.5 if in_pos == 1 else 3.5) * sd[j]
            elif in_pos != 0 and abs(zv[j]) < 0.5:
                in_pos = 0
        s_open = np.log(m["open_a"]) - np.log(m["open_b"])
        return dict(legs=("BTCUSDT", "ETHUSDT"), tf="1h",
                    s=np.asarray(s.values, float),
                    s_open=np.asarray(s_open.values, float),
                    side=side, stop_s=stop_s, beta=1.0,
                    ts=list(m["timestamp"].astype(str)),
                    bh=float((m["close_a"].iloc[-1] / m["close_a"].iloc[0] - 1)
                             * 100))

    if sid == 85:                                  # HYPE/SOL with a Kalman beta
        a = PK.load_klines("HYPEUSDT", "1h")
        b = PK.load_klines("SOLUSDT", "1h")
        m = PK.align(a, b)
        la = np.log(m["close_a"].values)
        lb = np.log(m["close_b"].values)
        n = len(m)
        beta = np.ones(n)
        b_est = 1.0
        P = 1.0
        Q = 1e-5
        R = 1e-3
        for i in range(n):
            if not (np.isfinite(la[i]) and np.isfinite(lb[i])):
                beta[i] = b_est
                continue
            P += Q
            x = lb[i]
            K = P * x / (x * x * P + R)
            resid = la[i] - b_est * lb[i]
            b_est += K * resid
            P *= (1 - K * x)
            beta[i] = b_est
        s = pd.Series(la - beta * lb)
        z = PK.zscore(s, 100)
        zv = z.values
        sd = s.rolling(100).std().values
        mean = s.rolling(100).mean().values
        side = np.zeros(n)
        stop_s = np.full(n, np.nan)
        in_pos = 0
        for j in range(n):
            if not np.isfinite(zv[j]):
                continue
            if in_pos == 0 and abs(zv[j]) > 2.0:
                in_pos = 1 if zv[j] < 0 else -1
                side[j] = in_pos
                stop_s[j] = mean[j] + in_pos * (-4.0 if in_pos == 1 else 4.0) * sd[j]
            elif in_pos != 0 and (zv[j] * in_pos < 0):
                in_pos = 0
        s_open = np.log(m["open_a"].values) - beta * np.log(m["open_b"].values)
        return dict(legs=("HYPEUSDT", "SOLUSDT"), tf="1h",
                    s=np.asarray(s.values, float),
                    s_open=np.asarray(s_open, float),
                    side=side, stop_s=stop_s, beta=beta,
                    ts=list(m["timestamp"].astype(str)),
                    bh=float((m["close_a"].iloc[-1] / m["close_a"].iloc[0] - 1)
                             * 100))

    if sid == 86:                                  # SUI/JUP cointegration
        a = PK.load_klines("SUIUSDT", "1h")
        b = PK.load_klines("JUPUSDT", "1h")
        m = PK.align(a, b)
        la = np.log(m["close_a"].values)
        lb = np.log(m["close_b"].values)
        n = len(m)
        W = 500
        beta = np.full(n, np.nan)
        resid = np.full(n, np.nan)
        pval_ok = np.zeros(n, dtype=bool)
        for j in range(W - 1, n):
            xa = la[j - W + 1:j + 1]
            xb = lb[j - W + 1:j + 1]
            X = np.column_stack([xb, np.ones(W)])
            try:
                coef, *_ = np.linalg.lstsq(X, xa, rcond=None)
            except Exception:
                continue
            b_hat = coef[0]
            r = xa - X @ coef
            beta[j] = b_hat
            resid[j] = r[-1]
            pval_ok[j] = PK._adf_tstat(r, lag=1) < -2.86
        s = pd.Series(resid)
        z = PK.zscore(s, 100)
        zv = z.values
        sd = s.rolling(100).std().values
        mean = s.rolling(100).mean().values
        side = np.zeros(n)
        stop_s = np.full(n, np.nan)
        in_pos = 0
        for j in range(n):
            if not np.isfinite(zv[j]) or not pval_ok[j]:
                continue
            if in_pos == 0 and abs(zv[j]) > 2.0:
                in_pos = 1 if zv[j] < 0 else -1
                side[j] = in_pos
                stop_s[j] = mean[j] + in_pos * (-4.0 if in_pos == 1 else 4.0) * sd[j]
            elif in_pos != 0 and (zv[j] * in_pos < 0):
                in_pos = 0
        s_log = la - beta * lb
        s_log = np.where(np.isfinite(s_log), s_log, 0.0)
        s_open = np.log(m["open_a"].values) - beta * np.log(m["open_b"].values)
        s_open = np.where(np.isfinite(s_open), s_open, s_log)
        use_beta = np.where(np.isfinite(beta), beta, 1.0)
        return dict(legs=("SUIUSDT", "JUPUSDT"), tf="1h",
                    s=np.asarray(s_log, float),
                    s_open=np.asarray(s_open, float),
                    side=side, stop_s=stop_s, beta=use_beta,
                    ts=list(m["timestamp"].astype(str)),
                    bh=float((m["close_a"].iloc[-1] / m["close_a"].iloc[0] - 1)
                             * 100))

    if sid == 88:
        # alt basket vs BTC: an equal-weight basket of five alts against
        # BTC, with a 168-bar rolling beta and the z-score of the 24-bar
        # relative return. The pack's own function, ported verbatim.
        alts = ["ETHUSDT", "SOLUSDT", "HYPEUSDT", "SUIUSDT", "JUPUSDT"]
        btc = PK.load_klines("BTCUSDT", "1h")
        frames = {s: PK.load_klines(s, "1h") for s in alts}
        base = btc[["open_ts", "open", "close"]].copy()
        base["timestamp"] = pd.to_datetime(base["open_ts"], unit="ms", utc=True)
        for s in alts:
            f = frames[s].set_index("open_ts")["close"]
            base[s] = base["open_ts"].map(f)
        base = base.sort_values("open_ts").reset_index(drop=True)

        norm = pd.DataFrame({"open_ts": base["open_ts"]})
        for s in alts:
            first_valid = base[s].first_valid_index()
            if first_valid is None:
                continue
            norm[s] = base[s] / base[s].iloc[first_valid]
        basket = norm.drop(columns=["open_ts"]).mean(axis=1, skipna=True).values

        lb = np.log(base["close"].values)
        la = np.log(basket)
        ret_a = pd.Series(la).diff(24).values
        ret_b = pd.Series(lb).diff(24).values
        diff = ret_a - ret_b
        zz = ((diff - pd.Series(diff).rolling(168).mean().values)
              / pd.Series(diff).rolling(168).std().values)

        ra = pd.Series(la).diff()
        rb = pd.Series(lb).diff()
        beta = (ra.rolling(168).cov(rb) / rb.rolling(168).var()).values
        beta = np.where(np.isfinite(beta), beta, 1.0)

        s = la - beta * lb
        sd = pd.Series(s).rolling(100).std().values
        side = np.zeros(len(base))
        stop_s = np.full(len(base), np.nan)
        in_pos = 0
        for j in range(len(base)):
            if not np.isfinite(zz[j]) or not np.isfinite(s[j]):
                continue
            if in_pos == 0 and abs(zz[j]) > 2.0:
                in_pos = -1 if zz[j] > 0 else 1
                side[j] = in_pos
                stop_s[j] = s[j] + (4.0 * sd[j] if in_pos == -1 else -4.0 * sd[j])
            elif in_pos != 0 and (zz[j] * in_pos < 0):
                in_pos = 0

        s_open = la - beta * lb
        return dict(legs=("ALT-BASKET", "BTCUSDT"), tf="1h",
                    s=np.asarray(s, float), s_open=np.asarray(s_open, float),
                    side=side, stop_s=stop_s, beta=beta,
                    ts=list(base["timestamp"].astype(str)),
                    bh=float((base["close"].iloc[-1] / base["close"].iloc[0] - 1)
                             * 100))

    if sid == 89:                                  # ETH/BTC ratio breakout
        a = PK.load_klines("ETHUSDT", "15m")
        b = PK.load_klines("BTCUSDT", "15m")
        m = PK.align(a, b)
        ratio = pd.Series(m["close_a"].values / m["close_b"].values)
        hi200 = ratio.rolling(200).max().values
        mean100 = ratio.rolling(100).mean().values
        atr_ratio = PK.atr(pd.DataFrame({"high": ratio, "low": ratio,
                                         "close": ratio}), 14).values
        side = np.zeros(len(m))
        stop_s = np.full(len(m), np.nan)
        in_pos = 0
        for j in range(200, len(m)):
            rj = ratio.iloc[j]
            if in_pos == 0 and rj > hi200[j - 1]:
                in_pos = 1
                side[j] = 1
                stop_s[j] = np.log(rj - 2.0 * atr_ratio[j])
            elif in_pos != 0 and rj < mean100[j]:
                in_pos = 0
        s = np.log(ratio.values)
        s_open = np.log(m["open_a"].values / m["open_b"].values)
        return dict(legs=("ETHUSDT", "BTCUSDT"), tf="15m",
                    s=np.asarray(s, float), s_open=np.asarray(s_open, float),
                    side=side, stop_s=stop_s, beta=1.0,
                    ts=list(m["timestamp"].astype(str)),
                    bh=float((m["close_a"].iloc[-1] / m["close_a"].iloc[0] - 1)
                             * 100))

    raise ValueError(f"prompt {sid} no es un par de spread")


# ═════════════════════════════════════════════════════════════════════════
# the BASKETS (83, 84, 87, 88, 90)
# ═══════════════════════════════════════════════════════════════════════
BASKETS = {
    83: dict(symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT",
                      "SUIUSDT", "JUPUSDT"], tf="1h", rank_window=168,
              rebalance_bars=168, mode="mom", top_k=2),
    84: dict(symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT",
                      "SUIUSDT", "JUPUSDT"], tf="1h", rank_window=24,
              rebalance_bars=24, mode="mom", top_k=1),
    87: dict(symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT",
                      "SUIUSDT", "JUPUSDT"], tf="1h", rank_window=20,
              rebalance_bars=168, mode="lowvol", top_k=2),
    90: dict(symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT",
                      "SUIUSDT", "JUPUSDT"], tf="1h", rank_window=336,
              rebalance_bars=168, mode="volscaled", top_k=2),
}


def basket_signal(sid: int) -> dict:
    """The signal arrays of a cross-sectional basket: the per-symbol ranking
    signal, the panel of closes and opens, the rebalance cadence and the leg
    weights.

    The pack's `cross_sectional` builds the panel, the ranking signal and the
    weights; here the arrays are returned instead of being traded, so the
    repo's book can execute them.
    """
    if sid in BASKETS:
        cfg = dict(BASKETS[sid])
    else:
        raise ValueError(f"prompt {sid} no es una cesta")

    symbols = cfg["symbols"]
    tf = cfg["tf"]
    frames = {s: PK.load_klines(s, tf)[["open_ts", "open", "close", "high", "low"]]
              for s in symbols}
    idx = sorted(set().union(*[set(f["open_ts"]) for f in frames.values()]))
    panel = pd.DataFrame({"open_ts": idx})
    for s in symbols:
        f = frames[s].set_index("open_ts")
        panel[s + "_close"] = panel["open_ts"].map(f["close"])
        panel[s + "_open"] = panel["open_ts"].map(f["open"])
        panel[s + "_high"] = panel["open_ts"].map(f["high"])
        panel[s + "_low"] = panel["open_ts"].map(f["low"])

    closes = {s: panel[s + "_close"].values for s in symbols}
    opens = {s: panel[s + "_open"].values for s in symbols}

    signal = {}
    for s in symbols:
        c = pd.Series(closes[s])
        if cfg["mode"] == "mom":
            signal[s] = c.pct_change(cfg["rank_window"]).values
        elif cfg["mode"] == "lowvol":
            atr_like = ((pd.Series(panel[s + "_high"].values)
                         - pd.Series(panel[s + "_low"].values)) / c)
            signal[s] = atr_like.rolling(20).mean().values
        elif cfg["mode"] == "volscaled":
            atr_like = ((pd.Series(panel[s + "_high"].values)
                         - pd.Series(panel[s + "_low"].values)) / c)
            atr_pct = atr_like.rolling(20).mean().values
            signal[s] = (c.pct_change(cfg["rank_window"]).values
                         / np.where(atr_pct > 0, atr_pct, np.nan))
        else:
            raise ValueError(cfg["mode"])

    rets = {s: pd.Series(closes[s]).pct_change().values for s in symbols}

    bh_rets = []
    for s in symbols:
        c = pd.Series(closes[s]).dropna()
        if len(c) > 1:
            bh_rets.append(c.iloc[-1] / c.iloc[0] - 1)
    bh = float(np.mean(bh_rets) * 100) if bh_rets else 0.0

    # the panel's index is the raw open_ts (epoch ms): to ISO strings, so the
    # engine's segment boundaries are computed on the right dates (reading
    # those ints as nanoseconds would put every bar in 1970)
    ts = [str(pd.Timestamp(int(x), unit="ms", tz="UTC")) for x in idx]
    return dict(symbols=symbols, tf=tf, closes=closes, opens=opens,
                rets=rets, signal=signal, mode=cfg["mode"], top_k=cfg["top_k"],
                rank_window=cfg["rank_window"],
                rebalance_bars=cfg["rebalance_bars"], ts=ts, bh=bh)
