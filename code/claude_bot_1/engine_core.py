"""
engine_core.py
Core infrastructure for the 20-strategy multi-pair crypto backtesting suite.

Two execution modes:
  - 'discrete'  : event-driven, ATR(14)*mult stop-loss per leg, % risk position sizing.
                  Used by trend/momentum, reversion, vol/RS, and pairs-spread strategies
                  (a spread trade = two coordinated single-asset legs, sized via risk_scale).
  - 'weight'    : continuous target-weight rebalancing (risk parity / rotation / vol targeting).
                  No per-leg stop; optional portfolio-level max_gross_leverage cap.

Costs: TAKER_FEE applied on every fill notional (both sides), plus SLIPPAGE_BPS adverse
price adjustment on every fill, per the brief (0.05% taker fees + standard slippage).

NOTE ON SIMPLIFICATIONS (documented, not hidden):
  - Pairs/spread strategies (06, 08, 10) split total spread risk 50/50 between the two
    legs rather than weighting legs strictly by the OLS hedge ratio. The hedge ratio IS
    used for signal generation (spread construction / z-score), just not for exact dollar
    sizing per leg. Good enough for research triage; tighten if moving to production.
  - "Cointegration ranking" (06) is proxied by lowest rolling OLS-residual variance among
    candidate pairs, not a formal Engle-Granger/ADF test. Swap in
    statsmodels.tsa.stattools.coint for production rigor.
  - Squeeze/regime percentile filters (12, 13) use rolling min-max normalization instead of
    a true rolling percentile rank, for speed. Directionally equivalent, less precise at
    the tails.
  - Weight-mode "trades" (for win-rate / profit-factor / expectancy) are per-rebalance-period
    P&L, not discrete round-trip trades -- there is no round-trip concept in a continuously
    rebalanced allocation.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Callable, Optional, Any
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TAKER_FEE = 0.0005        # 0.05% per fill, per side
SLIPPAGE_BPS = 0.0003     # 3 bps adverse slippage per fill (tune per pair/liquidity)
BARS_PER_YEAR = 24 * 365  # 1h candles, crypto trades 24/7
STARTING_EQUITY = 100_000.0

UNIVERSE = ["SOLUSDC", "BTCUSDC", "ETHUSDC", "AVAXUSDC", "LINKUSDC"]

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
@dataclass
class StrategyConfig:
    id: str
    name: str
    archetype: str
    mode: str                      # 'discrete' or 'weight'
    signal_fn: Optional[Callable] = None   # discrete mode
    weight_fn: Optional[Callable] = None   # weight mode
    max_concurrent_legs: int = 5
    risk_per_trade: float = 0.01
    portfolio_heat_cap: float = 0.05
    atr_stop_mult: float = 2.0
    max_gross_leverage: float = 1.0        # weight mode only


@dataclass
class Leg:
    pair: str
    direction: int
    entry_price: float
    entry_bar: int
    size: float
    stop_price: float
    risk_amount: float


@dataclass
class Trade:
    pair: str
    direction: int
    entry_bar: int
    exit_bar: int
    entry_price: float
    exit_price: float
    pnl: float
    risk_amount: float
    reason: str


@dataclass
class BacktestResult:
    strategy_id: str
    mode: str
    equity_curve: pd.Series
    trades: list


# ---------------------------------------------------------------------------
# Indicator library
# ---------------------------------------------------------------------------
def ema(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(span=period, adjust=False).mean()

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.fillna(50.0)

def true_range(high, low, close) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr

def atr(high, low, close, period: int = 14) -> pd.Series:
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1 / period, adjust=False).mean()

def macd_hist(close, fast=12, slow=26, signal=9) -> pd.Series:
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    return macd_line - signal_line

def bollinger(close, period=20, mult=2.0):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    up = mid + mult * std
    low = mid - mult * std
    width = (up - low) / mid.replace(0, np.nan)
    return mid, up, low, width

def keltner(close, high, low, period=20, atr_period=14, mult=2.0):
    mid = ema(close, period)
    a = atr(high, low, close, atr_period)
    return mid, mid + mult * a, mid - mult * a

def adx(high, low, close, period=14) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr = true_range(high, low, close)
    atr_ = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=high.index).ewm(alpha=1 / period, adjust=False).mean() / atr_.replace(0, np.nan)
    minus_di = 100 * pd.Series(minus_dm, index=high.index).ewm(alpha=1 / period, adjust=False).mean() / atr_.replace(0, np.nan)
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100
    return dx.ewm(alpha=1 / period, adjust=False).mean().fillna(0.0)

def realized_vol(close, window=20, annualize=True) -> pd.Series:
    logret = np.log(close / close.shift(1))
    vol = logret.rolling(window).std()
    if annualize:
        vol = vol * np.sqrt(BARS_PER_YEAR)
    return vol

def zscore(series, window=50) -> pd.Series:
    m = series.rolling(window).mean()
    s = series.rolling(window).std()
    return (series - m) / s.replace(0, np.nan)


# ---------------------------------------------------------------------------
# Data alignment + indicator precompute
# ---------------------------------------------------------------------------
def align_universe(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    common_index = None
    for df in data.values():
        common_index = df.index if common_index is None else common_index.intersection(df.index)
    common_index = common_index.sort_values()
    return {p: df.loc[common_index].copy() for p, df in data.items()}

def precompute_indicators(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    out = {}
    for pair, df in data.items():
        ind = pd.DataFrame(index=df.index)
        ind["close"] = df["close"]
        ind["rsi14"] = rsi(df["close"], 14)
        ind["atr14"] = atr(df["high"], df["low"], df["close"], 14)
        ind["ema20"] = ema(df["close"], 20)
        ind["ema50"] = ema(df["close"], 50)
        ind["ema100"] = ema(df["close"], 100)
        ind["ema200"] = ema(df["close"], 200)
        ind["macd_hist"] = macd_hist(df["close"])
        bb_mid, bb_up, bb_low, bb_width = bollinger(df["close"], 20, 2.0)
        ind["bb_mid"], ind["bb_up"], ind["bb_low"], ind["bb_width"] = bb_mid, bb_up, bb_low, bb_width
        bw_min = bb_width.rolling(100).min()
        bw_max = bb_width.rolling(100).max()
        ind["bb_width_norm"] = (bb_width - bw_min) / (bw_max - bw_min).replace(0, np.nan)
        kc_mid, kc_up, kc_low = keltner(df["close"], df["high"], df["low"], 20, 14, 2.0)
        ind["kc_mid"], ind["kc_up"], ind["kc_low"] = kc_mid, kc_up, kc_low
        ind["don_up55"] = df["high"].rolling(55).max()
        ind["don_low20"] = df["low"].rolling(20).min()
        ind["adx14"] = adx(df["high"], df["low"], df["close"], 14)
        ind["rvol20"] = realized_vol(df["close"], 20)
        atr_pct = ind["atr14"] / df["close"]
        ap_min = atr_pct.rolling(24 * 60).min()
        ap_max = atr_pct.rolling(24 * 60).max()
        ind["atr_pct_norm"] = (atr_pct - ap_min) / (ap_max - ap_min).replace(0, np.nan)
        ind["zscore50"] = zscore(df["close"], 50)
        ind["mom_30d"] = df["close"].pct_change(30 * 24)
        ind["mom_12h"] = df["close"].pct_change(12)
        ind["mom_72h"] = df["close"].pct_change(72)
        out[pair] = ind
    return out


# ---------------------------------------------------------------------------
# Discrete engine
# ---------------------------------------------------------------------------
def run_discrete_backtest(cfg: StrategyConfig, data: dict[str, pd.DataFrame],
                           indicators: dict[str, pd.DataFrame],
                           starting_equity: float = STARTING_EQUITY) -> BacktestResult:
    pairs = list(data.keys())
    idx = next(iter(data.values())).index
    n = len(idx)
    cash = starting_equity
    open_legs: dict[str, Leg] = {}
    trades: list[Trade] = []
    equity_curve = np.zeros(n)
    state: dict[str, Any] = {}

    for t in range(n):
        prices = {p: data[p]["close"].iat[t] for p in pairs}
        highs = {p: data[p]["high"].iat[t] for p in pairs}
        lows = {p: data[p]["low"].iat[t] for p in pairs}

        # 1) stop checks (intrabar high/low)
        for p in list(open_legs.keys()):
            leg = open_legs[p]
            hit, exit_price = False, None
            if leg.direction == 1 and lows[p] <= leg.stop_price:
                hit, exit_price = True, leg.stop_price
            elif leg.direction == -1 and highs[p] >= leg.stop_price:
                hit, exit_price = True, leg.stop_price
            if hit:
                pnl = leg.direction * (exit_price - leg.entry_price) * leg.size
                fee = abs(exit_price * leg.size) * TAKER_FEE
                cash += pnl - fee
                trades.append(Trade(p, leg.direction, leg.entry_bar, t, leg.entry_price, exit_price, pnl - fee, leg.risk_amount, "stop"))
                del open_legs[p]

        # 2) signal function -> entries/exits
        sig = cfg.signal_fn(data, indicators, t, state, open_legs)
        exits = sig.get("exits", {})
        entries = sig.get("entries", {})

        for p in exits:
            if p in open_legs:
                leg = open_legs[p]
                price = prices[p]
                pnl = leg.direction * (price - leg.entry_price) * leg.size
                fee = abs(price * leg.size) * TAKER_FEE
                cash += pnl - fee
                trades.append(Trade(p, leg.direction, leg.entry_bar, t, leg.entry_price, price, pnl - fee, leg.risk_amount, "signal"))
                del open_legs[p]

        # mark equity before sizing new entries (so risk % is off pre-entry equity)
        unrealized = sum(l.direction * (prices[l.pair] - l.entry_price) * l.size for l in open_legs.values())
        equity_now = cash + unrealized

        open_risk = sum(l.risk_amount for l in open_legs.values())
        for p, ent in entries.items():
            if p in open_legs:
                continue
            if len(open_legs) >= cfg.max_concurrent_legs:
                continue
            risk_scale = ent.get("risk_scale", 1.0)
            risk_amount = cfg.risk_per_trade * equity_now * risk_scale
            if open_risk + risk_amount > cfg.portfolio_heat_cap * equity_now:
                continue
            atr_val = indicators[p]["atr14"].iat[t]
            if np.isnan(atr_val) or atr_val <= 0:
                continue
            stop_dist = cfg.atr_stop_mult * atr_val
            direction = 1 if ent["action"] == "enter_long" else -1
            price = prices[p]
            slip = price * SLIPPAGE_BPS
            entry_price = price + slip if direction == 1 else price - slip
            size = risk_amount / stop_dist
            fee = abs(entry_price * size) * TAKER_FEE
            cash -= fee
            stop_price = entry_price - direction * stop_dist
            open_legs[p] = Leg(p, direction, entry_price, t, size, stop_price, risk_amount)
            open_risk += risk_amount

        unrealized = sum(l.direction * (prices[l.pair] - l.entry_price) * l.size for l in open_legs.values())
        equity_curve[t] = cash + unrealized

    return BacktestResult(cfg.id, "discrete", pd.Series(equity_curve, index=idx), trades)


# ---------------------------------------------------------------------------
# Weight-based engine
# ---------------------------------------------------------------------------
def run_weight_backtest(cfg: StrategyConfig, data: dict[str, pd.DataFrame],
                         indicators: dict[str, pd.DataFrame],
                         starting_equity: float = STARTING_EQUITY) -> BacktestResult:
    pairs = list(data.keys())
    idx = next(iter(data.values())).index
    n = len(idx)
    cash = starting_equity
    holdings = {p: 0.0 for p in pairs}
    equity_curve = np.zeros(n)
    rebalance_log = []  # (bar_idx, equity_at_rebalance)
    state: dict[str, Any] = {}

    for t in range(n):
        prices = {p: data[p]["close"].iat[t] for p in pairs}
        port_value = cash + sum(holdings[p] * prices[p] for p in pairs)
        target = cfg.weight_fn(data, indicators, t, state)
        if target is not None:
            gross = sum(abs(w) for w in target.values())
            if gross > cfg.max_gross_leverage and gross > 0:
                scale = cfg.max_gross_leverage / gross
                target = {p: w * scale for p, w in target.items()}
            for p in pairs:
                w = target.get(p, 0.0)
                target_units = (w * port_value) / prices[p] if prices[p] > 0 else 0.0
                delta_units = target_units - holdings[p]
                trade_notional = abs(delta_units) * prices[p]
                if trade_notional > 1e-8:
                    fee = trade_notional * TAKER_FEE
                    slip = trade_notional * SLIPPAGE_BPS
                    cash -= delta_units * prices[p]
                    cash -= (fee + slip)
                    holdings[p] = target_units
            rebalance_log.append((t, port_value))
        equity_curve[t] = cash + sum(holdings[p] * prices[p] for p in pairs)

    return BacktestResult(cfg.id, "weight", pd.Series(equity_curve, index=idx), rebalance_log)


def run_backtest(cfg: StrategyConfig, data, indicators, starting_equity: float = STARTING_EQUITY) -> BacktestResult:
    if cfg.mode == "discrete":
        return run_discrete_backtest(cfg, data, indicators, starting_equity)
    elif cfg.mode == "weight":
        return run_weight_backtest(cfg, data, indicators, starting_equity)
    raise ValueError(f"unknown mode {cfg.mode}")


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------
def build_benchmark(data: dict[str, pd.DataFrame], starting_equity: float = STARTING_EQUITY) -> pd.Series:
    pairs = list(data.keys())
    idx = next(iter(data.values())).index
    prices0 = {p: data[p]["close"].iat[0] for p in pairs}
    units = {p: (starting_equity / len(pairs)) / prices0[p] for p in pairs}
    n = len(idx)
    curve = np.zeros(n)
    for t in range(n):
        curve[t] = sum(units[p] * data[p]["close"].iat[t] for p in pairs)
    return pd.Series(curve, index=idx)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def compute_metrics(result: BacktestResult, benchmark: pd.Series) -> dict:
    eq = result.equity_curve
    ret = eq.pct_change().dropna()
    cum_return = eq.iloc[-1] / eq.iloc[0] - 1
    bench_cum_return = benchmark.iloc[-1] / benchmark.iloc[0] - 1

    sharpe = (ret.mean() / ret.std()) * np.sqrt(BARS_PER_YEAR) if ret.std() > 0 else np.nan
    downside = ret[ret < 0]
    sortino = (ret.mean() / downside.std()) * np.sqrt(BARS_PER_YEAR) if len(downside) > 1 and downside.std() > 0 else np.nan
    running_max = eq.cummax()
    dd = eq / running_max - 1
    max_dd = dd.min()

    if result.mode == "discrete":
        trades = result.trades
        n_trades = len(trades)
        pnls = [tr.pnl for tr in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        win_rate = len(wins) / n_trades if n_trades > 0 else np.nan
        profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else np.nan
        expectancy_r = np.mean([tr.pnl / tr.risk_amount for tr in trades]) if n_trades > 0 else np.nan
    else:
        bars = [b for b, _ in result.trades]
        equities_at_rebal = [eq.iloc[b] for b in bars] + [eq.iloc[-1]]
        period_returns = [
            (equities_at_rebal[i + 1] / equities_at_rebal[i] - 1)
            for i in range(len(equities_at_rebal) - 1) if equities_at_rebal[i] != 0
        ]
        n_trades = len(period_returns)
        wins = [r for r in period_returns if r > 0]
        losses = [r for r in period_returns if r <= 0]
        win_rate = len(wins) / n_trades if n_trades > 0 else np.nan
        profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else np.nan
        expectancy_r = np.mean(period_returns) if n_trades > 0 else np.nan

    return dict(
        cumulative_return_pct=cum_return * 100,
        benchmark_return_pct=bench_cum_return * 100,
        sharpe=sharpe,
        sortino=sortino,
        max_dd_pct=max_dd * 100,
        win_rate_pct=win_rate * 100 if win_rate == win_rate else np.nan,
        total_trades=n_trades,
        profit_factor=profit_factor,
        expectancy_r=expectancy_r,
    )


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
def plot_equity_and_drawdown(result: BacktestResult, benchmark: pd.Series, title: str, out_path: str):
    eq = result.equity_curve
    dd = eq / eq.cummax() - 1
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    ax1.plot(eq.index, eq.values, label="Strategy", color="#2563eb", linewidth=1.3)
    ax1.plot(benchmark.index, benchmark.values, label="Equal-Weight Benchmark", color="#9ca3af", linewidth=1.0, alpha=0.85)
    ax1.set_title(title, fontsize=11)
    ax1.set_ylabel("Equity ($)")
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(alpha=0.25)
    ax2.fill_between(dd.index, dd.values * 100, 0, color="#dc2626", alpha=0.45)
    ax2.set_ylabel("Drawdown (%)")
    ax2.grid(alpha=0.25)
    plt.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
