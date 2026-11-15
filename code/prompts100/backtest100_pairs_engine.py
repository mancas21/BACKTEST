#!/usr/bin/env python3
"""
100-Prompt Backtest Pack — Multi-pair engine (strategies 81-90)
===============================================================

Conventions carried over from the single-pair engine:
- signal on the closed bar, fill at the next bar's open
- stop evaluated on bar close, exit filled at the next open
- 11 bps round trip (5.5 bps per side) applied to both legs
- 1% equity risk per trade, sized from the distance to the z-stop
- 70/30 IS/OOS split, fresh capital at the start of each segment

Spread P&L model
----------------
For a dollar-neutral pair with hedge ratio beta:
    s_t = log(A_t) - beta * log(B_t)
A position of side q is long N USDT of A and short beta*N of B.
P&L over a spread move ds is approximately N * ds (log-return approximation),
so N is chosen as risk_amount / |s_stop - s_entry|.

Deviations from the prompt text (documented in the output):
- 84's "2 ATR-normalized units" for 88 is implemented as a 168-bar z-score of
  the 24-bar relative return spread, since a return difference has no price ATR.
- 86 uses a rolling 500-bar Engle-Granger residual with an ADF(1) t-stat against
  the -2.86 5% critical value instead of a full statsmodels EG test on every bar.
- 85 uses a scalar Kalman filter on beta (random-walk state), intercept fixed at 0.
- Cross-sectional baskets (83/84/87/90) use 1x gross dollar-neutral exposure per
  rebalance instead of 1%-risk sizing, because a basket has no single stop.
"""

from __future__ import annotations
import os, math, json
import numpy as np
import pandas as pd

DATA_DIR = r"C:\Users\Lenovo\Documents\backtest-system\data"
OUT_DIR = r"C:\Users\Lenovo\Downloads\backtest100_results"
os.makedirs(OUT_DIR, exist_ok=True)

COST_PER_SIDE = 0.000055
ROUND_TRIP = 2 * COST_PER_SIDE

TF_DIR = {"1h": "binance_klines_1h", "15m": "binance_klines_15m", "5m": "binance_klines_5m"}
BARS_PER_YEAR = {"1h": 8760.0, "15m": 35040.0, "5m": 105120.0}


def load_klines(symbol, tf):
    path = os.path.join(DATA_DIR, TF_DIR[tf], symbol + "_" + tf + ".csv")
    df = pd.read_csv(path)
    df = df.sort_values("open_ts").drop_duplicates("open_ts").reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
    return df


def align(a, b):
    """Inner-join two kline frames on open_ts."""
    cols = ["open_ts", "open", "high", "low", "close", "volume"]
    m = pd.merge(a[cols], b[cols], on="open_ts", suffixes=("_a", "_b"))
    m = m.sort_values("open_ts").reset_index(drop=True)
    m["timestamp"] = pd.to_datetime(m["open_ts"], unit="ms", utc=True)
    return m


def zscore(s, window):
    mean = s.rolling(window).mean()
    sd = s.rolling(window).std()
    return (s - mean) / sd


def atr(df, period=14):
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def compute_metrics(equity, trades, bh_return_pct, bars_per_year):
    eq = np.asarray(equity, dtype=float)
    if len(eq) < 2:
        return dict(total_return_pct=0.0, max_dd_pct=0.0, profit_factor=None,
                    n_trades=0, win_rate=0.0, sharpe=0.0, bh_return_pct=bh_return_pct,
                    avg_r=0.0)
    rets = np.diff(eq) / eq[:-1]
    rets = rets[np.isfinite(rets)]
    total = (eq[-1] / eq[0] - 1) * 100
    peak = np.maximum.accumulate(eq)
    max_dd = ((eq - peak) / peak).min() * 100
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    losses = [t["pnl"] for t in trades if t["pnl"] < 0]
    gp, gl = sum(wins), -sum(losses)
    pf = (gp / gl) if gl > 0 else (float("inf") if gp > 0 else None)
    wr = len(wins) / len(trades) * 100 if trades else 0.0
    sharpe = (rets.mean() / rets.std() * math.sqrt(bars_per_year)) if len(rets) > 1 and rets.std() > 0 else 0.0
    avg_r = float(np.mean([t["r"] for t in trades])) if trades else 0.0
    return dict(total_return_pct=total, max_dd_pct=max_dd,
                profit_factor=(pf if pf is None or math.isfinite(pf) else None),
                n_trades=len(trades), win_rate=wr, sharpe=sharpe,
                bh_return_pct=bh_return_pct, avg_r=avg_r)


class SpreadSim:
    """Bar-by-bar spread simulator with next-open fills."""

    def __init__(self, s_close, s_open, timestamps, beta, initial_equity=10000.0,
                 risk_pct=0.01, cost_per_side=COST_PER_SIDE):
        self.s = np.asarray(s_close, dtype=float)
        self.so = np.asarray(s_open, dtype=float)
        self.ts = timestamps
        self.beta = beta if np.isscalar(beta) else np.asarray(beta, dtype=float)
        self.eq0 = initial_equity
        self.risk_pct = risk_pct
        self.cost = cost_per_side

    def beta_at(self, j):
        return float(self.beta[j]) if not np.isscalar(self.beta) else float(self.beta)

    def run(self, side_target, stop_s, start, end):
        """
        side_target[j] in {-1, 0, +1}: desired position after bar j closes.
        stop_s[j]: spread level that stops a position entered at bar j+1.
        Stops are detected on the close of bar j and filled at the next open.
        """
        cash = self.eq0
        pos = None
        trades = []
        curve = []

        def close_pos(exit_idx, exit_s, reason):
            nonlocal cash, pos
            pnl_gross = pos["N"] * pos["side"] * (exit_s - pos["entry_s"])
            fee_exit = pos["N"] * (1 + self.beta_at(exit_idx)) * self.cost
            cash += pnl_gross - fee_exit
            pnl = pnl_gross - fee_exit - pos["fees_entry"]
            trades.append(dict(side=pos["side"], entry_time=pos["entry_time"],
                               exit_time=str(self.ts[exit_idx]), pnl=pnl,
                               r=pnl / pos["risk"], reason=reason))
            pos = None

        for j in range(start, end + 1):
            stopped = False
            if pos is not None and j > pos["entry_idx"]:
                hit = (pos["side"] == 1 and self.s[j] <= pos["stop_s"]) or \
                      (pos["side"] == -1 and self.s[j] >= pos["stop_s"])
                if hit:
                    close_pos(j + 1 if j + 1 < len(self.s) else j, self.so[j + 1] if j + 1 < len(self.so) else self.s[j], "stop")
                    stopped = True

            # mark to market (entry fee already deducted from cash)
            if pos is not None:
                upnl = pos["N"] * pos["side"] * (self.s[j] - pos["entry_s"])
                curve.append(cash + upnl)
            else:
                curve.append(cash)

            if j >= end:
                break

            tgt = side_target[j]
            if pos is not None and tgt != pos["side"]:
                close_pos(j + 1, self.so[j + 1], "signal")

            if pos is None and not stopped and tgt != 0 and np.isfinite(stop_s[j]):
                entry_s = self.so[j + 1]
                dist = abs(stop_s[j] - entry_s)
                if dist > 1e-9:
                    risk = cash * self.risk_pct
                    N = min(risk / dist, cash * 20.0)
                    fee_entry = N * (1 + self.beta_at(j)) * self.cost
                    cash -= fee_entry
                    pos = dict(side=tgt, N=N, entry_s=entry_s, stop_s=stop_s[j],
                               entry_idx=j + 1, entry_time=str(self.ts[j + 1]),
                               fees_entry=fee_entry, risk=risk)

        if pos is not None:
            close_pos(end, self.s[end], "end_of_data")

        return curve, trades


def run_is_oos(sim, side_target, stop_s, bh_pct, bars_per_year, oos_frac=0.3):
    n = len(sim.s)
    split = int(n * (1 - oos_frac))
    is_curve, is_tr = sim.run(side_target, stop_s, 0, split - 1)
    oos_curve, oos_tr = sim.run(side_target, stop_s, split, n - 1)
    m_is = compute_metrics(is_curve, is_tr, bh_pct, bars_per_year)
    m_oos = compute_metrics(oos_curve, oos_tr, 0.0, bars_per_year)
    return m_is, m_oos


def make_result(strategy, legs, tf, m_is, m_oos):
    return dict(strategy=strategy, legs=legs, tf=tf,
                is_return_pct=round(m_is["total_return_pct"], 2),
                is_max_dd_pct=round(m_is["max_dd_pct"], 2),
                is_pf=None if m_is["profit_factor"] is None else round(m_is["profit_factor"], 3),
                is_trades=m_is["n_trades"], is_win_rate=round(m_is["win_rate"], 1),
                is_sharpe=round(m_is["sharpe"], 3), bh_return_pct=round(m_is["bh_return_pct"], 2),
                oos_return_pct=round(m_oos["total_return_pct"], 2),
                oos_max_dd_pct=round(m_oos["max_dd_pct"], 2),
                oos_pf=None if m_oos["profit_factor"] is None else round(m_oos["profit_factor"], 3),
                oos_trades=m_oos["n_trades"], oos_win_rate=round(m_oos["win_rate"], 1),
                oos_sharpe=round(m_oos["sharpe"], 3))


# ============================ 81 SOL/ETH z-score ============================
def strat_81():
    a = load_klines("SOLUSDT", "1h")
    b = load_klines("ETHUSDT", "1h")
    m = align(a, b)
    s = np.log(m["close_a"]) - np.log(m["close_b"])
    z = zscore(s, 100)
    side = np.zeros(len(m))
    stop_s = np.full(len(m), np.nan)
    in_pos = 0
    sd = s.rolling(100).std().values
    mean = s.rolling(100).mean().values
    zv = z.values
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
    sim = SpreadSim(s.values, s_open.values, m["timestamp"].values.astype("datetime64[ns]").astype(str) if False else list(m["timestamp"].astype(str)), beta=1.0)
    bh = (m["close_a"].iloc[-1] / m["close_a"].iloc[0] - 1) * 100
    mi, mo = run_is_oos(sim, side, stop_s, bh, BARS_PER_YEAR["1h"])
    return make_result(81, "SOL-ETH", "1h", mi, mo)


# ============================ 82 BTC/ETH z-score ============================
def strat_82():
    a = load_klines("BTCUSDT", "1h")
    b = load_klines("ETHUSDT", "1h")
    m = align(a, b)
    s = np.log(m["close_a"]) - np.log(m["close_b"])
    z = zscore(s, 100)
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
    sim = SpreadSim(s.values, s_open.values, list(m["timestamp"].astype(str)), beta=1.0)
    bh = (m["close_a"].iloc[-1] / m["close_a"].iloc[0] - 1) * 100
    mi, mo = run_is_oos(sim, side, stop_s, bh, BARS_PER_YEAR["1h"])
    return make_result(82, "BTC-ETH", "1h", mi, mo)


# ==================== cross-sectional basket engine ====================
def cross_sectional(symbols, tf, rank_window, rebalance_bars, mode, top_k=2):
    frames = {s: load_klines(s, tf)[["open_ts", "open", "close", "high", "low"]] for s in symbols}
    idx = sorted(set().union(*[set(f["open_ts"]) for f in frames.values()]))
    # build panel with NaN where a symbol has no bar
    panel = pd.DataFrame({"open_ts": idx})
    for s in symbols:
        f = frames[s].set_index("open_ts")
        panel[s + "_close"] = panel["open_ts"].map(f["close"])
        panel[s + "_open"] = panel["open_ts"].map(f["open"])
        panel[s + "_high"] = panel["open_ts"].map(f["high"])
        panel[s + "_low"] = panel["open_ts"].map(f["low"])

    closes = {s: panel[s + "_close"].values for s in symbols}
    opens = {s: panel[s + "_open"].values for s in symbols}
    n = len(panel)

    # signal per symbol
    signal = {}
    for s in symbols:
        c = pd.Series(closes[s])
        if mode == "mom":
            signal[s] = c.pct_change(rank_window).values
        elif mode == "lowvol":
            r = c.pct_change()
            atr_like = (pd.Series(panel[s + "_high"].values) - pd.Series(panel[s + "_low"].values)) / c
            signal[s] = atr_like.rolling(20).mean().values
        elif mode == "volscaled":
            r = c.pct_change()
            atr_like = (pd.Series(panel[s + "_high"].values) - pd.Series(panel[s + "_low"].values)) / c
            atr_pct = atr_like.rolling(20).mean().values
            signal[s] = c.pct_change(rank_window).values / np.where(atr_pct > 0, atr_pct, np.nan)
        else:
            raise ValueError(mode)

    # returns per bar
    rets = {}
    for s in symbols:
        c = pd.Series(closes[s])
        rets[s] = c.pct_change().values

    # simulate
    eq0 = 10000.0
    cash = eq0
    curve = []
    trades = []
    weights = {s: 0.0 for s in symbols}
    last_rebal = -10 ** 9
    bh_start = {s: closes[s][0] for s in symbols}

    def book_pnl(j):
        tot = 0.0
        for s in symbols:
            if weights[s] != 0.0 and np.isfinite(rets[s][j]):
                tot += weights[s] * rets[s][j]
        return tot

    def do_rebalance(j):
        nonlocal cash, last_rebal
        avail = [s for s in symbols if np.isfinite(signal[s][j]) and np.isfinite(closes[s][j])]
        if len(avail) < 2 * top_k:
            return
        ranked = sorted(avail, key=lambda s: signal[s][j])
        if mode == "lowvol":
            longs = ranked[:top_k]      # lowest ATR% long
            shorts = ranked[-top_k:]    # highest ATR% short
        else:
            longs = ranked[-top_k:]
            shorts = ranked[:top_k]
        new_w = {s: 0.0 for s in symbols}
        leg = 1.0 / (2 * top_k)
        for s in longs:
            new_w[s] = leg
        for s in shorts:
            new_w[s] = -leg
        turnover = sum(abs(new_w[s] - weights[s]) for s in symbols)
        fee = turnover * cash * COST_PER_SIDE
        cash -= fee
        weights.update(new_w)
        last_rebal = j

    for j in range(1, n - 1):
        pnl = book_pnl(j)
        cash *= (1 + pnl)
        curve.append(cash)
        if j - last_rebal >= rebalance_bars:
            if last_rebal > -10 ** 8:
                trades.append(dict(pnl=cash - pending_start_equity,
                                   r=(cash / pending_start_equity - 1) if pending_start_equity else 0.0,
                                   reason="basket"))
            do_rebalance(j)
            pending_start_equity = cash

    if last_rebal > -10 ** 8:
        trades.append(dict(pnl=cash - pending_start_equity,
                           r=(cash / pending_start_equity - 1) if pending_start_equity else 0.0,
                           reason="basket"))

    # basket buy & hold (equal weight, available symbols)
    bh_rets = []
    for s in symbols:
        c = pd.Series(closes[s]).dropna()
        if len(c) > 1:
            bh_rets.append(c.iloc[-1] / c.iloc[0] - 1)
    bh = float(np.mean(bh_rets) * 100) if bh_rets else 0.0

    # split IS/OOS on curve
    split = int(len(curve) * 0.7)
    m_is = compute_metrics(curve[:split], [t for t in trades if t["reason"] == "basket"][:max(1, int(len(trades) * 0.7))], bh, BARS_PER_YEAR[tf])
    m_oos = compute_metrics(curve[split - 1:], [t for t in trades if t["reason"] == "basket"][int(len(trades) * 0.7):], 0.0, BARS_PER_YEAR[tf])
    return m_is, m_oos


def strat_83():
    mi, mo = cross_sectional(["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "SUIUSDT", "JUPUSDT"],
                             "1h", 168, 168, "mom", top_k=2)
    return make_result(83, "6-perp basket", "1h", mi, mo)


def strat_84():
    mi, mo = cross_sectional(["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "SUIUSDT", "JUPUSDT"],
                             "1h", 24, 24, "mom", top_k=1)
    return make_result(84, "6-perp basket", "1h", mi, mo)


def strat_87():
    mi, mo = cross_sectional(["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "SUIUSDT", "JUPUSDT"],
                             "1h", 20, 168, "lowvol", top_k=2)
    return make_result(87, "6-perp basket", "1h", mi, mo)


def strat_90():
    mi, mo = cross_sectional(["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "SUIUSDT", "JUPUSDT"],
                             "1h", 336, 168, "volscaled", top_k=2)
    return make_result(90, "6-perp basket", "1h", mi, mo)


# ==================== 85 HYPE/SOL Kalman ====================
def strat_85():
    a = load_klines("HYPEUSDT", "1h")
    b = load_klines("SOLUSDT", "1h")
    m = align(a, b)
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
    z = zscore(s, 100)
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
    sim = SpreadSim(s.values, s_open, list(m["timestamp"].astype(str)), beta=beta)
    bh = (m["close_a"].iloc[-1] / m["close_a"].iloc[0] - 1) * 100
    mi, mo = run_is_oos(sim, side, stop_s, bh, BARS_PER_YEAR["1h"])
    return make_result(85, "HYPE-SOL", "1h", mi, mo)


# ==================== 86 SUI/JUP cointegration ====================
def _adf_tstat(resid, lag=1):
    """ADF(1) t-stat on a residual window: regress de_t on e_{t-1}, de_{t-1}."""
    e = np.asarray(resid, dtype=float)
    de = np.diff(e)
    if len(de) < lag + 3:
        return 0.0
    y = de[lag:]
    X = [e[lag:-1]]
    for k in range(1, lag + 1):
        X.append(de[lag - k:-k])
    X = np.column_stack(X)
    X = np.column_stack([X, np.ones(len(X))])
    try:
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid_reg = y - X @ coef
        dof = len(y) - X.shape[1]
        sigma2 = (resid_reg @ resid_reg) / dof
        cov = sigma2 * np.linalg.inv(X.T @ X)
        se = math.sqrt(max(cov[0, 0], 1e-18))
        return coef[0] / se
    except Exception:
        return 0.0


def strat_86():
    a = load_klines("SUIUSDT", "1h")
    b = load_klines("JUPUSDT", "1h")
    m = align(a, b)
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
        pval_ok[j] = _adf_tstat(r, lag=1) < -2.86

    s = pd.Series(resid)
    z = zscore(s, 100)
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

    # spread in log space using the contemporaneous hedge ratio
    s_log = la - beta * lb
    s_log = np.where(np.isfinite(s_log), s_log, 0.0)
    s_open = np.log(m["open_a"].values) - beta * np.log(m["open_b"].values)
    s_open = np.where(np.isfinite(s_open), s_open, s_log)
    use_beta = np.where(np.isfinite(beta), beta, 1.0)
    sim = SpreadSim(s_log, s_open, list(m["timestamp"].astype(str)), beta=use_beta)
    bh = (m["close_a"].iloc[-1] / m["close_a"].iloc[0] - 1) * 100
    mi, mo = run_is_oos(sim, side, stop_s, bh, BARS_PER_YEAR["1h"])
    return make_result(86, "SUI-JUP", "1h", mi, mo)


# ==================== 88 alt basket vs BTC ====================
def strat_88():
    alts = ["ETHUSDT", "SOLUSDT", "HYPEUSDT", "SUIUSDT", "JUPUSDT"]
    btc = load_klines("BTCUSDT", "1h")
    frames = {s: load_klines(s, "1h") for s in alts}
    # use BTC index, forward-fill basket members that have no bar yet
    base = btc[["open_ts", "open", "close"]].copy()
    base["timestamp"] = pd.to_datetime(base["open_ts"], unit="ms", utc=True)
    for s in alts:
        f = frames[s].set_index("open_ts")["close"]
        base[s] = base["open_ts"].map(f)
    base = base.sort_values("open_ts").reset_index(drop=True)

    # equal-weight basket index from each member's cumulative return, equal weight on available members
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
    zz = (diff - pd.Series(diff).rolling(168).mean().values) / pd.Series(diff).rolling(168).std().values

    # rolling beta of basket returns on BTC returns
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
            in_pos = -1 if zz[j] > 0 else 1   # basket outperforms -> short basket, long BTC
            side[j] = in_pos
            stop_s[j] = s[j] + (4.0 * sd[j] if in_pos == -1 else -4.0 * sd[j])
        elif in_pos != 0 and (zz[j] * in_pos < 0):
            in_pos = 0

    # spread open uses basket/btc open ratio scaled to same basis as la
    s_open = la - beta * lb
    sim = SpreadSim(s, s_open, list(base["timestamp"].astype(str)), beta=beta)
    bh = (base["close"].iloc[-1] / base["close"].iloc[0] - 1) * 100
    mi, mo = run_is_oos(sim, side, stop_s, bh, BARS_PER_YEAR["1h"])
    return make_result(88, "ALT-BTC", "1h", mi, mo)


# ==================== 89 ETH/BTC ratio breakout ====================
def strat_89():
    a = load_klines("ETHUSDT", "15m")
    b = load_klines("BTCUSDT", "15m")
    m = align(a, b)
    ratio = pd.Series(m["close_a"].values / m["close_b"].values)
    hi200 = ratio.rolling(200).max().values
    mean100 = ratio.rolling(100).mean().values
    atr_ratio = atr(pd.DataFrame({"high": ratio, "low": ratio, "close": ratio}), 14).values

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
    sim = SpreadSim(s, s_open, list(m["timestamp"].astype(str)), beta=1.0)
    bh = (m["close_a"].iloc[-1] / m["close_a"].iloc[0] - 1) * 100
    mi, mo = run_is_oos(sim, side, stop_s, bh, BARS_PER_YEAR["15m"])
    return make_result(89, "ETH-BTC", "15m", mi, mo)


RUNNERS = {81: strat_81, 82: strat_82, 83: strat_83, 84: strat_84, 85: strat_85,
           86: strat_86, 87: strat_87, 88: strat_88, 89: strat_89, 90: strat_90}


def main():
    rows = []
    for num in sorted(RUNNERS):
        print("Strategy %d..." % num, end=" ", flush=True)
        try:
            r = RUNNERS[num]()
            rows.append(r)
            print("OK  IS %.2f%%  OOS %.2f%%  PF %s  trades %d" % (
                r["is_return_pct"], r["oos_return_pct"], r["oos_pf"], r["oos_trades"]), flush=True)
        except Exception as e:
            print("ERROR: %s" % str(e)[:200], flush=True)
    df = pd.DataFrame(rows)
    out = os.path.join(OUT_DIR, "results_multipair_81_90.csv")
    df.to_csv(out, index=False)
    print("\nSaved", out)
    if len(df):
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
