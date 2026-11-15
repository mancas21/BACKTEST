#!/usr/bin/env python3
"""
100-Prompt Backtest Pack — Core Engine
=====================================

Engine assumptions (from the prompt file):
- Signal on closed bar t, fill at next open t+1
- 1% risk per trade from ATR(14) stop
- Stop wins ties (if stop and target both hit on same bar, stop takes precedence)
- Intrabar stop/target evaluated on high/low of the fill bar
- Fees and slippage on: default 11 bps round trip (5.5 bps per side)
- Full history per pair, 70/30 IS/OOS split
- Long-only mean-reversion strategies; trend strategies can be long/short
- No pyramiding: one position per symbol at a time

Outputs per strategy:
- Net return %, max drawdown %, profit factor, trade count, win rate, Sharpe
- Buy & hold comparison
- OOS profit factor (on 30% holdout)
- Equity curve
"""

from __future__ import annotations
import os, math, json
import numpy as np
import pandas as pd

# ============================ Cost configuration ============================
# Round-trip costs: 11 bps default (5.5 bps per side)
FEE_PER_SIDE = 0.000055   # 5.5 bps
SLIP_PER_SIDE = 0.0       # slippage folded into fee for simplicity
COST_PER_SIDE = FEE_PER_SIDE + SLIP_PER_SIDE
COST_ROUND_TRIP = 2 * COST_PER_SIDE  # 11 bps

RISK_PCT = 0.01  # 1% risk per trade

# ============================ Data loading ============================
DATA_1H = r"C:\Users\Lenovo\Documents\backtest-system\data\binance_klines_1h"
DATA_15M = r"C:\Users\Lenovo\Documents\backtest-system\data\binance_klines_15m"
DATA_5M = r"C:\Users\Lenovo\Documents\backtest-system\data\binance_klines_5m"
DATA_FUNDING = r"C:\Users\Lenovo\Documents\backtest-system\data\binance_funding"

PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "SUIUSDT", "JUPUSDT"]

def load_klines(symbol, tf):
    """Load klines CSV for a symbol/timeframe."""
    path = os.path.join(
        r"C:\Users\Lenovo\Documents\backtest-system\data",
        "binance_klines_" + tf,
        symbol + "_" + tf + ".csv",
    )
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
    df = df.sort_values("open_ts").reset_index(drop=True)
    return df

def load_funding(symbol):
    """Load funding history JSON."""
    path = os.path.join(DATA_FUNDING, symbol + "_funding.json")
    with open(path) as f:
        data = json.load(f)
    records = [{"t": int(x["t"]), "r": float(x["r"])} for x in data if "t" in x and "r" in x]
    df = pd.DataFrame(records)
    if len(df):
        df["timestamp"] = pd.to_datetime(df["t"], unit="ms", utc=True)
        df = df.sort_values("t").reset_index(drop=True)
    return df

# ============================ Indicators ============================
def ema(x, span):
    return x.ewm(span=span, adjust=False).mean()

def sma(x, span):
    return x.rolling(span).mean()

def rsi(x, period=14):
    delta = x.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def atr(df, period=14):
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def bollinger(x, period=20, num_std=2.0):
    mid = sma(x, period)
    sd = x.rolling(period).std()
    return mid, mid + num_std * sd, mid - num_std * sd

def keltner(df, period=20, mult=1.5):
    mid = ema(df["close"], period)
    atr_val = atr(df, period)
    return mid, mid + mult * atr_val, mid - mult * atr_val

def donchian(df, period):
    hi = df["high"].rolling(period).max()
    lo = df["low"].rolling(period).min()
    return hi, lo

def macd(x):
    e12 = ema(x, 12)
    e26 = ema(x, 26)
    m = e12 - e26
    sig = ema(m, 9)
    return m, sig, m - sig

def adx(df, period=14):
    h, l, c = df["high"], df["low"], df["close"]
    up = h - h.shift(1)
    down = l.shift(1) - l
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = atr(df, period)
    plus_di = 100 * pd.Series(plus_dm).ewm(alpha=1/period, adjust=False).mean() / tr
    minus_di = 100 * pd.Series(minus_dm).ewm(alpha=1/period, adjust=False).mean() / tr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.ewm(alpha=1/period, adjust=False).mean(), plus_di, minus_di

def stochastic(df, k_period=14, d_period=3):
    low_min = df["low"].rolling(k_period).min()
    high_max = df["high"].rolling(k_period).max()
    k = 100 * (df["close"] - low_min) / (high_max - low_min)
    d = k.ewm(span=d_period, adjust=False).mean()
    return k, d

def williams_r(df, period=14):
    high_max = df["high"].rolling(period).max()
    low_min = df["low"].rolling(period).min()
    return -100 * (high_max - df["close"]) / (high_max - low_min)

def cci(df, period=20):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma_tp = tp.rolling(period).mean()
    mean_dev = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    return (tp - sma_tp) / (0.015 * mean_dev)

def vwap(df):
    """Session VWAP (resets daily at 00:00 UTC)."""
    df = df.copy()
    df["date"] = df["timestamp"].dt.date
    df["typical"] = (df["high"] + df["low"] + df["close"]) / 3
    df["vp"] = df["typical"] * df["volume"]
    df["cum_vp"] = df.groupby("date")["vp"].cumsum()
    df["cum_vol"] = df.groupby("date")["volume"].cumsum()
    df["vwap"] = df["cum_vp"] / df["cum_vol"]
    return df["vwap"]

def supertrend(df, period=10, multiplier=3.0):
    hl2 = (df["high"] + df["low"]) / 2
    atr_val = atr(df, period)
    upper = hl2 + multiplier * atr_val
    lower = hl2 - multiplier * atr_val
    st = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    st.iloc[0] = lower.iloc[0]
    direction.iloc[0] = 1
    for i in range(1, len(df)):
        if df["close"].iloc[i-1] <= st.iloc[i-1]:
            st.iloc[i] = min(upper.iloc[i], st.iloc[i-1])
            direction.iloc[i] = 1
        else:
            st.iloc[i] = max(lower.iloc[i], st.iloc[i-1])
            direction.iloc[i] = -1
    return st, direction

def rolling_beta(series1, series2, window):
    """Rolling beta of series1 on series2."""
    cov = series1.rolling(window).cov(series2)
    var = series2.rolling(window).var()
    return cov / var

def rolling_corr(series1, series2, window):
    return series1.rolling(window).corr(series2)

def hull_ma(x, period):
    """Hull Moving Average."""
    wma1 = x.ewm(span=period//2, adjust=False).mean()
    wma2 = x.ewm(span=period, adjust=False).mean()
    raw = 2 * wma1 - wma2
    return raw.ewm(span=int(math.sqrt(period)), adjust=False).mean()

def parabolic_sar(df, af_start=0.02, af_step=0.02, af_max=0.2):
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    n = len(df)
    sar = np.zeros(n)
    trend = np.zeros(n)  # 1 = long, -1 = short
    af = np.zeros(n)
    ep = np.zeros(n)
    
    sar[0] = low[0]
    trend[0] = 1
    af[0] = af_start
    ep[0] = high[0]
    
    for i in range(1, n):
        if trend[i-1] == 1:
            sar[i] = sar[i-1] + af[i-1] * (ep[i-1] - sar[i-1])
            if low[i] < sar[i]:
                trend[i] = -1
                sar[i] = ep[i-1]
                af[i] = af_start
                ep[i] = low[i]
            else:
                trend[i] = 1
                if high[i] > ep[i-1]:
                    ep[i] = high[i]
                    af[i] = min(af[i-1] + af_step, af_max)
                else:
                    ep[i] = ep[i-1]
                    af[i] = af[i-1]
        else:
            sar[i] = sar[i-1] + af[i-1] * (ep[i-1] - sar[i-1])
            if high[i] > sar[i]:
                trend[i] = 1
                sar[i] = ep[i-1]
                af[i] = af_start
                ep[i] = high[i]
            else:
                trend[i] = -1
                if low[i] < ep[i-1]:
                    ep[i] = low[i]
                    af[i] = min(af[i-1] + af_step, af_max)
                else:
                    ep[i] = ep[i-1]
                    af[i] = af[i-1]
    return sar, trend

def ultimate_oscillator(df, p1=7, p2=14, p3=28):
    close = df["close"]
    low = df["low"]
    prev_close = close.shift(1)
    tr = pd.concat([
        df["high"] - low,
        (df["high"] - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    
    bp = close - pd.concat([low, prev_close], axis=1).min(axis=1)
    
    avg1 = bp.rolling(p1).sum() / tr.rolling(p1).sum()
    avg2 = bp.rolling(p2).sum() / tr.rolling(p2).sum()
    avg3 = bp.rolling(p3).sum() / tr.rolling(p3).sum()
    
    return 100 * (4 * avg1 + 2 * avg2 + avg3) / 7

def mfi(df, period=14):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    rm = tp * df["volume"]
    df = df.copy()
    df["tr"] = tp
    df["rm"] = rm
    df["prev_tr"] = df["tr"].shift(1)
    df["pmf"] = np.where(df["tr"] > df["prev_tr"], df["rm"], 0.0)
    df["nmf"] = np.where(df["tr"] < df["prev_tr"], df["rm"], 0.0)
    mfr = df["pmf"].rolling(period).sum() / df["nmf"].rolling(period).sum()
    return 100 - (100 / (1 + mfr))

def aroon(df, period=25):
    def aroon_up(arr):
        return (period - 1 - np.argmin(arr[::-1])) / period * 100
    def aroon_down(arr):
        return (period - 1 - np.argmax(arr[::-1])) / period * 100
    up = df["high"].rolling(period).apply(aroon_up, raw=True)
    down = df["low"].rolling(period).apply(aroon_down, raw=True)
    return up, down

def kama(x, period=10):
    """Kaufman Adaptive Moving Average."""
    change = x.diff(period).abs()
    volatility = x.diff().abs().rolling(period).sum()
    er = change / volatility
    sc = (er * (2 / (2 + 1) - 2 / (period + 1)) + 2 / (period + 1)) ** 2
    kama = pd.Series(index=x.index, dtype=float)
    kama.iloc[period] = x.iloc[period]
    for i in range(period + 1, len(x)):
        kama.iloc[i] = kama.iloc[i-1] + sc.iloc[i] * (x.iloc[i] - kama.iloc[i-1])
    return kama

def vwma(x, volume, period):
    return (x * volume).rolling(period).sum() / volume.rolling(period).sum()

# ============================ Backtest Engine ============================
class Position:
    __slots__ = ("side", "qty", "entry", "stop", "tp", "entry_idx", "entry_time", "risk_amount", "max_hold")
    def __init__(self, side, qty, entry, stop, tp, entry_idx, entry_time, risk_amount, max_hold=None):
        self.side = side        # +1 long, -1 short
        self.qty = qty
        self.entry = entry      # fill price
        self.stop = stop        # stop price
        self.tp = tp            # take profit price (None = no TP)
        self.entry_idx = entry_idx
        self.entry_time = entry_time
        self.risk_amount = risk_amount
        self.max_hold = max_hold

class BacktestResult:
    def __init__(self, strategy_name, symbol, tf, total_return_pct, max_dd_pct,
                 profit_factor, n_trades, win_rate, sharpe, bh_return_pct,
                 oos_pf, equity_curve, trades, is_return_pct, oos_return_pct):
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.tf = tf
        self.total_return_pct = total_return_pct
        self.max_dd_pct = max_dd_pct
        self.profit_factor = profit_factor
        self.n_trades = n_trades
        self.win_rate = win_rate
        self.sharpe = sharpe
        self.bh_return_pct = bh_return_pct
        self.oos_pf = oos_pf
        self.equity_curve = equity_curve
        self.trades = trades
        self.is_return_pct = is_return_pct
        self.oos_return_pct = oos_return_pct

class Engine:
    def __init__(self, df, initial_equity=10000.0, cost_per_side=COST_PER_SIDE,
                 risk_pct=RISK_PCT, max_leverage=20.0):
        self.df = df.reset_index(drop=True)
        self.n = len(df)
        self.open_ = df["open"].values
        self.high = df["high"].values
        self.low = df["low"].values
        self.close = df["close"].values
        self.initial_equity = initial_equity
        self.cost_per_side = cost_per_side
        self.risk_pct = risk_pct
        # No exchange offers unbounded leverage. 1%-risk sizing on a near-zero ATR
        # stop would otherwise imply astronomically large notional, so cap it at 20x
        # equity per position (within Binance Futures limits for these pairs).
        self.max_leverage = max_leverage
        
        self.equity = initial_equity
        self.cash = initial_equity
        self.position = None
        self.trades = []
        self.equity_curve = []
        
    def mark_to_market(self, idx):
        """Equity at close of bar idx."""
        if self.position is None:
            return self.cash
        px = self.close[idx]
        if self.position.side == 1:
            return self.cash + self.position.qty * px
        else:
            return self.cash - self.position.qty * px
    
    def open_position(self, idx, side, entry_px, stop_px, tp_px=None, max_hold=None):
        """Open a position at the open of bar idx+1 (filled at open of idx+1)."""
        if self.position is not None:
            return False
        fill_px = entry_px * (1 + side * self.cost_per_side)
        # If the opening gap has already carried price through the stop (or through
        # the target), the setup is invalid: entering would book a fictitious fill at
        # a stop that is on the wrong side of the market. Skip the trade instead.
        if side == 1:
            if fill_px <= stop_px:
                return False
            if tp_px is not None and fill_px >= tp_px:
                return False
        else:
            if fill_px >= stop_px:
                return False
            if tp_px is not None and fill_px <= tp_px:
                return False
        dist = abs(stop_px - entry_px)
        if dist <= 0:
            return False
        risk_amount = self.equity * self.risk_pct
        qty = risk_amount / dist
        max_qty = self.max_leverage * self.equity / fill_px
        if qty > max_qty:
            qty = max_qty
        notional = qty * fill_px
        fee = notional * self.cost_per_side
        
        if side == 1:
            self.cash -= qty * fill_px + fee
        else:
            self.cash += qty * fill_px - fee
        
        self.position = Position(side, qty, fill_px, stop_px, tp_px, idx+1,
                                 self.df["timestamp"].iloc[idx+1] if idx+1 < self.n else None,
                                 risk_amount, max_hold)
        return True
    
    def close_position(self, idx, exit_px, reason="signal"):
        """Close position at the open of bar idx."""
        if self.position is None:
            return None
        p = self.position
        fill_px = exit_px * (1 - p.side * self.cost_per_side)
        notional = p.qty * fill_px
        fee = notional * self.cost_per_side
        
        if p.side == 1:
            pnl = p.qty * (fill_px - p.entry) - fee
            self.cash += p.qty * fill_px - fee
        else:
            pnl = p.qty * (p.entry - fill_px) - fee
            self.cash -= p.qty * fill_px + fee
        
        self.equity = self.cash
        r = pnl / p.risk_amount if p.risk_amount and p.risk_amount != 0 else 0.0
        
        trade = {
            "entry_idx": p.entry_idx,
            "exit_idx": idx,
            "entry_time": str(p.entry_time),
            "exit_time": str(self.df["timestamp"].iloc[idx]),
            "side": "long" if p.side == 1 else "short",
            "qty": p.qty,
            "entry": p.entry,
            "exit": fill_px,
            "pnl": pnl,
            "fee": fee,
            "r": r,
            "reason": reason,
        }
        self.trades.append(trade)
        self.position = None
        return trade
    
    def check_stop_tp(self, idx):
        """Check intrabar stop/TP on bar idx. Returns (exit_px, reason) or None.

        A bar that opens beyond the stop fills at the open (gap loss); a bar that
        merely trades through it fills at the stop. The stop is checked before the
        target, so the stop wins when both are touched.
        """
        if self.position is None:
            return None
        p = self.position
        hi = self.high[idx]
        lo = self.low[idx]
        op = self.open_[idx]

        if p.side == 1:
            # Long: stop below, TP above
            if op <= p.stop:
                return op, "stop_gap"
            if lo <= p.stop:
                return p.stop, "stop"
            if p.tp is not None and hi >= p.tp:
                return p.tp, "tp"
        else:
            # Short: stop above, TP below
            if op >= p.stop:
                return op, "stop_gap"
            if hi >= p.stop:
                return p.stop, "stop"
            if p.tp is not None and lo <= p.tp:
                return p.tp, "tp"
        return None
    
    def run(self, signal_fn, start_idx=0, end_idx=None):
        """
        Run the backtest.
        signal_fn(idx, ctx) -> dict with keys:
            'side': +1 (long), -1 (short), 0 (flat/exit)
            'stop_px': stop price (required if side != 0)
            'tp_px': take profit price (optional)
        ctx provides access to dataframe and indicators.
        """
        if end_idx is None:
            end_idx = self.n - 1
        
        self.equity = self.initial_equity
        self.cash = self.initial_equity
        self.position = None
        self.trades = []
        self.equity_curve = []
        
        for j in range(start_idx, end_idx + 1):
            # 1. Time stop: close at the open of the bar following the holding limit
            if self.position is not None and self.position.max_hold is not None:
                if j - self.position.entry_idx >= self.position.max_hold:
                    self.close_position(j, self.open_[j], "time")
            
            # 2. Check stop/TP intrabar on current bar j
            if self.position is not None:
                result = self.check_stop_tp(j)
                if result is not None:
                    exit_px, reason = result
                    self.close_position(j, exit_px, reason)
            
            # 3. Record equity at close of bar j
            self.equity = self.mark_to_market(j)
            self.equity_curve.append(self.equity)
            
            # 4. Get signal for next bar (fill at open of j+1)
            if j >= end_idx:
                break
            
            ctx = {"df": self.df, "j": j}
            sig = signal_fn(j, ctx)
            
            if sig is None:
                continue
            
            side = sig.get("side", 0)
            if side == 0:
                # Exit signal
                if self.position is not None:
                    self.close_position(j + 1, self.open_[j + 1], "signal")
                continue
            
            stop_px = sig.get("stop_px")
            tp_px = sig.get("tp_px")
            max_hold = sig.get("max_hold")
            
            if stop_px is None:
                continue
            
            # Opposite-side signal reverses an open position at the same next open
            if self.position is not None and side != self.position.side:
                self.close_position(j + 1, self.open_[j + 1], "reverse")
            
            # Enter at open of j+1
            entry_px = self.open_[j + 1]
            self.open_position(j, side, entry_px, stop_px, tp_px, max_hold)
        
        # Close any remaining position at end
        if self.position is not None:
            self.close_position(end_idx, self.close[end_idx], "end_of_data")
        
        self.equity_curve.append(self.equity)
        
        # Compute metrics
        return self._compute_metrics(start_idx, end_idx)
    
    def _compute_metrics(self, start_idx, end_idx):
        eq = np.array(self.equity_curve)
        if len(eq) < 2:
            return BacktestResult("", "", "", 0, 0, 0, 0, 0, 0, 0, 0, eq, [], 0, 0)
        
        returns = np.diff(eq) / eq[:-1]
        returns = returns[~np.isnan(returns)]
        
        total_ret = (eq[-1] / eq[0] - 1) * 100
        
        # Max drawdown
        peak = np.maximum.accumulate(eq)
        dd = (eq - peak) / peak
        max_dd = dd.min() * 100
        
        # Profit factor
        wins = [t["pnl"] for t in self.trades if t["pnl"] > 0]
        losses = [t["pnl"] for t in self.trades if t["pnl"] < 0]
        gross_profit = sum(wins)
        gross_loss = -sum(losses)
        pf = gross_profit / gross_loss if gross_loss > 0 else (float('inf') if gross_profit > 0 else 0)
        
        n_trades = len(self.trades)
        win_rate = len(wins) / n_trades * 100 if n_trades > 0 else 0
        
        # Sharpe (hourly, annualized)
        if len(returns) > 1 and returns.std() > 0:
            # Assume hourly bars; annualize with sqrt(8760)
            sharpe = returns.mean() / returns.std() * math.sqrt(8760)
        else:
            sharpe = 0
        
        # Buy & hold
        bh_start = self.close[start_idx]
        bh_end = self.close[end_idx]
        bh_ret = (bh_end / bh_start - 1) * 100
        
        return {
            "total_return_pct": total_ret,
            "max_dd_pct": max_dd,
            "profit_factor": pf if math.isfinite(pf) else None,
            "n_trades": n_trades,
            "win_rate": win_rate,
            "sharpe": sharpe,
            "bh_return_pct": bh_ret,
            "equity_curve": eq.tolist(),
            "trades": self.trades,
        }

def run_is_oos(df, signal_fn, oos_frac=0.3):
    """Run backtest with 70/30 IS/OOS split. Returns IS and OOS results separately."""
    n = len(df)
    split_idx = int(n * (1 - oos_frac))
    
    # IS: from start to split_idx
    engine_is = Engine(df)
    is_metrics = engine_is.run(signal_fn, start_idx=0, end_idx=split_idx - 1)
    
    # OOS: from split_idx to end (need warmup for indicators - just use from split_idx)
    # But positions don't carry over; fresh start for OOS
    engine_oos = Engine(df)
    oos_metrics = engine_oos.run(signal_fn, start_idx=split_idx, end_idx=n - 1)
    
    return is_metrics, oos_metrics

# ============================ Strategy Registry ============================
STRATEGIES = {}

def register(name):
    def decorator(fn):
        STRATEGIES[name] = fn
        return fn
    return decorator
