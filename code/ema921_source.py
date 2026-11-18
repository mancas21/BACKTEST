#!/usr/bin/env python3
"""
9-21 EMA Crossover Strategy - Python backtest port
Source: "9-21 EMA Crossover Strategy" infographic (6 levels).

Rules implemented
  1. Trend:   EMA9 > EMA21 = up, EMA9 < EMA21 = down
  2. Signal:  EMA9 crosses EMA21 (bullish -> BUY, bearish -> SELL)
  3. Entry:   next candle open after the crossover bar closes
  4. SL:      long  -> below recent swing low  (rolling N-bar low at signal bar, + optional ATR buffer)
              short -> above recent swing high
  5. Target:  fixed R:R (default 1:2). Infographic also says "next S/R" - not codable
              without a level engine, so RR is used.
  6. Exit:    price crosses the opposite EMA (see exit_mode) OR TP hit OR SL hit.
              An opposite EMA crossover always closes and flips (it is the opposite signal).
  Tip filter: "do not trade sideways" -> optional ADX / EMA-spread filters (off by default).

Execution model (no lookahead)
  - Signals evaluated on bar close, filled at next bar open (+slippage).
  - SL/TP checked intrabar. Gap through level -> fill at open. SL and TP in same bar -> SL wins.
  - Signal exits (price-cross / opposite cross) fill at next open.
  - Fees per side on notional. Slippage applied to market fills (entry, SL, signal exit), not TP.
  - Sizing: risk_pct of equity per trade over SL distance, capped by max_leverage. Compounding.

Usage
  python ema_9_21_backtest.py --synthetic
  python ema_9_21_backtest.py --csv data/SUIUSDT_1h.csv --tf 1h
  python ema_9_21_backtest.py --symbol SUI/USDT:USDT --tf 1h --days 180      (needs ccxt)
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd


# ----------------------------------------------------------------------------
# Params
# ----------------------------------------------------------------------------
@dataclass
class Params:
    fast: int = 9
    slow: int = 21
    allow_long: bool = True
    allow_short: bool = True

    # stop loss
    swing_lookback: int = 10        # rolling N-bar low/high at signal bar
    sl_atr_buffer: float = 0.0      # extra ATR multiples beyond swing (0 = raw swing)
    atr_len: int = 14
    min_sl_pct: float = 0.10        # skip trade if SL distance < this % of entry

    # target / exit
    rr: float = 2.0
    use_tp: bool = True
    exit_mode: str = "price_slow"   # price_slow | price_fast | none  (opposite crossover always exits)

    # sideways filters (0 = off)
    adx_min: float = 0.0
    adx_len: int = 14
    min_spread_pct: float = 0.0     # |EMA9-EMA21| / close * 100 at signal bar

    # costs / sizing
    fee_bps: float = 4.0            # per side (Binance USDT-M taker ~4 bps)
    slip_bps: float = 1.0
    risk_pct: float = 1.0           # % equity risked per trade
    max_leverage: float = 5.0
    initial_equity: float = 10_000.0


# ----------------------------------------------------------------------------
# Indicators (Pine-style: EMA/RMA seeded with SMA)
# ----------------------------------------------------------------------------
def ema(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    out[n - 1] = x[:n].mean()
    a = 2.0 / (n + 1)
    for i in range(n, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def rma(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    valid = np.where(~np.isnan(x))[0]
    if len(valid) == 0:
        return out
    k = valid[0]
    if len(x) < k + n:
        return out
    out[k + n - 1] = x[k:k + n].mean()
    for i in range(k + n, len(x)):
        out[i] = (out[i - 1] * (n - 1) + x[i]) / n
    return out


def true_range(h, l, c):
    tr = np.empty(len(c))
    tr[0] = h[0] - l[0]
    pc = c[:-1]
    tr[1:] = np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - pc), np.abs(l[1:] - pc)])
    return tr


def atr_wilder(h, l, c, n):
    return rma(true_range(h, l, c), n)


def adx_wilder(h, l, c, n):
    up = np.zeros(len(c))
    dn = np.zeros(len(c))
    up[1:] = h[1:] - h[:-1]
    dn[1:] = l[:-1] - l[1:]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr_s = rma(true_range(h, l, c), n)
    pdi = 100 * rma(pdm, n) / tr_s
    mdi = 100 * rma(mdm, n) / tr_s
    dx = 100 * np.abs(pdi - mdi) / np.where((pdi + mdi) == 0, np.nan, pdi + mdi)
    return rma(dx, n)


# ----------------------------------------------------------------------------
# Engine
# ----------------------------------------------------------------------------
def run_backtest(df: pd.DataFrame, p: Params):
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    idx = df.index
    n = len(df)

    fast = ema(c, p.fast)
    slow = ema(c, p.slow)
    atr = atr_wilder(h, l, c, p.atr_len)
    adx = adx_wilder(h, l, c, p.adx_len) if p.adx_min > 0 else None
    warm = max(p.slow, p.atr_len, 2 * p.adx_len) + 2

    fee = p.fee_bps / 1e4
    slip = p.slip_bps / 1e4
    equity = p.initial_equity
    eq_curve = np.full(n, np.nan)

    pos = 0
    qty = entry = sl = tp = risk_amt = entry_fee = 0.0
    entry_i = 0
    pend_exit = False
    pend_entry = 0
    pend_sl = np.nan
    trades: list[dict] = []

    def close_trade(i, px, reason):
        nonlocal pos, equity, qty
        exit_fee = qty * px * fee
        gross = qty * (px - entry) * pos
        net = gross - exit_fee - entry_fee
        equity += gross - exit_fee      # entry fee already deducted at open
        trades.append(dict(
            entry_time=idx[entry_i], exit_time=idx[i], side="long" if pos == 1 else "short",
            entry=entry, exit=px, sl=sl, tp=tp, qty=qty, bars=i - entry_i,
            pnl=net, R=net / risk_amt if risk_amt else np.nan, reason=reason,
            equity=equity,
        ))
        pos = 0
        qty = 0.0

    for i in range(n):
        # 1) pending signal exit -> next open
        if pos and pend_exit:
            close_trade(i, o[i] * (1 - slip * pos), "signal")
        pend_exit = False

        # 2) pending entry -> next open
        if pos == 0 and pend_entry != 0:
            d = pend_entry
            px = o[i] * (1 + slip * d)
            risk_u = (px - pend_sl) * d
            if risk_u > 0 and risk_u / px * 100 >= p.min_sl_pct:
                qty = min(equity * p.risk_pct / 100 / risk_u, equity * p.max_leverage / px)
                risk_amt = qty * risk_u
                entry_fee = qty * px * fee
                equity -= entry_fee
                pos, entry, sl, entry_i = d, px, pend_sl, i
                tp = px + d * p.rr * risk_u if p.use_tp else np.nan
        pend_entry = 0

        # 3) intrabar SL / TP
        if pos:
            d = pos
            if i > entry_i:  # gap through level at open
                if (o[i] - sl) * d <= 0:
                    close_trade(i, o[i], "SL_gap")
                elif p.use_tp and (o[i] - tp) * d >= 0:
                    close_trade(i, o[i], "TP_gap")
            if pos:
                hit_sl = (l[i] <= sl) if d == 1 else (h[i] >= sl)
                hit_tp = p.use_tp and ((h[i] >= tp) if d == 1 else (l[i] <= tp))
                if hit_sl:
                    close_trade(i, sl * (1 - slip * d), "SL")
                elif hit_tp:
                    close_trade(i, tp, "TP")

        # 4) bar-close logic: signals for next open
        if i >= warm and not np.isnan(slow[i]) and not np.isnan(slow[i - 1]):
            xu = fast[i] > slow[i] and fast[i - 1] <= slow[i - 1]
            xd = fast[i] < slow[i] and fast[i - 1] >= slow[i - 1]

            if pos:
                d = pos
                if (d == 1 and xd) or (d == -1 and xu):
                    pend_exit = True
                elif p.exit_mode != "none":
                    ref = slow if p.exit_mode == "price_slow" else fast
                    if d == 1 and c[i - 1] >= ref[i - 1] and c[i] < ref[i]:
                        pend_exit = True
                    elif d == -1 and c[i - 1] <= ref[i - 1] and c[i] > ref[i]:
                        pend_exit = True

            sig = 1 if xu else (-1 if xd else 0)
            if sig == 1 and not p.allow_long:
                sig = 0
            if sig == -1 and not p.allow_short:
                sig = 0
            if sig:
                ok = True
                if adx is not None and not (adx[i] >= p.adx_min):
                    ok = False
                if p.min_spread_pct > 0 and abs(fast[i] - slow[i]) / c[i] * 100 < p.min_spread_pct:
                    ok = False
                if ok and (pos == 0 or pos == -sig):
                    buf = p.sl_atr_buffer * (atr[i] if not np.isnan(atr[i]) else 0.0)
                    lo = max(0, i - p.swing_lookback + 1)
                    pend_sl = (l[lo:i + 1].min() - buf) if sig == 1 else (h[lo:i + 1].max() + buf)
                    pend_entry = sig
                    if pos == -sig:
                        pend_exit = True  # flip

        # 5) mark-to-market
        eq_curve[i] = equity + (qty * (c[i] - entry) * pos if pos else 0.0)

    # close any open trade at last close (mark only)
    if pos:
        close_trade(n - 1, c[-1], "eod")
        eq_curve[-1] = equity

    eq = pd.Series(eq_curve, index=idx, name="equity")
    return pd.DataFrame(trades), eq


# ----------------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------------
def metrics(trades: pd.DataFrame, eq: pd.Series, p: Params) -> dict:
    out: dict = {}
    dt = pd.Series(eq.index).diff().dt.total_seconds().median()
    bpy = 365 * 24 * 3600 / dt if dt and dt > 0 else np.nan
    r = eq.pct_change().dropna()
    years = (eq.index[-1] - eq.index[0]).total_seconds() / (365 * 24 * 3600)
    total = eq.iloc[-1] / p.initial_equity - 1
    dd = (eq / eq.cummax() - 1).min()
    out["bars"] = len(eq)
    out["total_return_%"] = total * 100
    out["cagr_%"] = ((1 + total) ** (1 / years) - 1) * 100 if years > 0 and total > -1 else np.nan
    out["sharpe"] = r.mean() / r.std() * np.sqrt(bpy) if r.std() > 0 else np.nan
    dn = r[r < 0].std()
    out["sortino"] = r.mean() / dn * np.sqrt(bpy) if dn and dn > 0 else np.nan
    out["max_dd_%"] = dd * 100
    out["calmar"] = out["cagr_%"] / abs(out["max_dd_%"]) if dd < 0 else np.nan
    out["trades"] = len(trades)
    if len(trades):
        w = trades[trades.pnl > 0]
        ls = trades[trades.pnl <= 0]
        out["win_rate_%"] = len(w) / len(trades) * 100
        out["profit_factor"] = w.pnl.sum() / abs(ls.pnl.sum()) if len(ls) and ls.pnl.sum() != 0 else np.inf
        out["expectancy_R"] = trades.R.mean()
        out["avg_win_R"] = w.R.mean() if len(w) else np.nan
        out["avg_loss_R"] = ls.R.mean() if len(ls) else np.nan
        out["avg_bars"] = trades.bars.mean()
        out["long_trades"] = int((trades.side == "long").sum())
        out["short_trades"] = int((trades.side == "short").sum())
        out["long_pnl"] = trades[trades.side == "long"].pnl.sum()
        out["short_pnl"] = trades[trades.side == "short"].pnl.sum()
        out["exit_reasons"] = trades.reason.value_counts().to_dict()
    return out


# ----------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------
def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    tcol = next(c for c in ("timestamp", "time", "open_time", "datetime", "date") if c in df.columns)
    t = df[tcol]
    if np.issubdtype(t.dtype, np.number):
        unit = "ms" if t.iloc[0] > 1e11 else "s"
        df.index = pd.to_datetime(t, unit=unit, utc=True)
    else:
        df.index = pd.to_datetime(t, utc=True)
    df = df[["open", "high", "low", "close"] + (["volume"] if "volume" in df.columns else [])]
    return df.sort_index()[~df.index.duplicated()].astype(float)


def fetch_binance(symbol: str, tf: str, days: int) -> pd.DataFrame:
    import ccxt  # pip install ccxt
    ex = ccxt.binanceusdm({"enableRateLimit": True})
    since = ex.milliseconds() - days * 86_400_000
    rows = []
    while True:
        b = ex.fetch_ohlcv(symbol, tf, since=since, limit=1500)
        if not b:
            break
        rows += b
        since = b[-1][0] + 1
        if len(b) < 1500:
            break
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df.index = pd.to_datetime(df.pop("timestamp"), unit="ms", utc=True)
    return df.iloc[:-1]  # drop forming bar


def synthetic(n: int = 4000, seed: int = 7) -> pd.DataFrame:
    """Regime-switching random walk (trend / chop) for smoke tests only."""
    rng = np.random.default_rng(seed)
    drift = np.zeros(n)
    vol = np.zeros(n)
    i = 0
    while i < n:
        L = int(rng.integers(150, 500))
        trend = rng.random() < 0.5
        drift[i:i + L] = rng.choice([-1, 1]) * 0.0006 if trend else 0.0
        vol[i:i + L] = 0.004 if trend else 0.003
        i += L
    ret = drift + vol * rng.standard_normal(n)
    close = 100 * np.exp(np.cumsum(ret))
    open_ = np.r_[close[0], close[:-1]]
    spread = np.abs(rng.standard_normal(n)) * vol * close * 0.6
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    idx = pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                         "volume": rng.random(n) * 1000}, index=idx)


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="9-21 EMA crossover backtest")
    ap.add_argument("--csv")
    ap.add_argument("--symbol", default="SUI/USDT:USDT")
    ap.add_argument("--tf", default="1h")
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--out", default=".", help="dir for trades.csv / equity.csv")
    d = Params()
    for k, v in asdict(d).items():
        if isinstance(v, bool):
            ap.add_argument(f"--{k}", type=lambda s: s.lower() in ("1", "true", "yes"), default=v)
        else:
            ap.add_argument(f"--{k}", type=type(v), default=v)
    a = ap.parse_args()
    p = Params(**{k: getattr(a, k) for k in asdict(d)})

    if a.synthetic:
        df = synthetic()
    elif a.csv:
        df = load_csv(a.csv)
    else:
        df = fetch_binance(a.symbol, a.tf, a.days)

    trades, eq = run_backtest(df, p)
    m = metrics(trades, eq, p)

    print(f"\n{df.index[0]} -> {df.index[-1]}  ({len(df)} bars)")
    print(f"params: {asdict(p)}\n")
    for k, v in m.items():
        print(f"{k:>16}: {v:,.3f}" if isinstance(v, float) else f"{k:>16}: {v}")

    import os
    os.makedirs(a.out, exist_ok=True)
    trades.to_csv(os.path.join(a.out, "trades.csv"), index=False)
    eq.to_csv(os.path.join(a.out, "equity.csv"))


if __name__ == "__main__":
    main()
