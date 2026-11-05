#!/usr/bin/env python3
"""
sax_v4_engine.py — Swift Algo X v4.4 (audited) as a backtestable Python engine.

Pine<->Python parity: this file mirrors SAX_v4_strategy.pine rule for rule (same defaults, same
formulas, same execution model). Research only: no live orders, no exchange connectivity.

────────────────────────── AUDIT SUMMARY of the v4.4 indicator ──────────────────────────
CRITICAL
 C1 Intrabar repaint: signals, alerts, trade sim and optimizer run on the unconfirmed live bar; the
    optimizer's `var` arrays are mutated on every realtime tick (collection contents are not rolled
    back), so live counts can double count (verify on your chart).
 C2 FVG filter is dead: the zone is created and invalidated on the same bar (low <= zone_top is true
    on creation), so enabling it blocks every signal.
 C4 Streak sim recomputes TP/SL from the CURRENT bar's ATR every bar (moving targets); the drawn lines
    and the optimizer freeze them at entry, so the three disagree.
 C5 Optimizer = 132 combos ranked on the last 500 bars with min 5 trades, in-sample only, expectancy in
    raw price units, AM not multiplied by crypto_scale (main engine does), SL not optimised. Winner's curse.
HIGH
 H1 MTF requests lower timeframes (1m/3m/5m) from a higher chart; consensus of 8 correlated EMA20/50
    trends; "Suavizado" mode scales |dn| by the bull share, so it can still pass counter-trend entries;
    hard floor of 2/8 is nearly meaningless.
 H2 No fees/slippage, entry at the signal bar close, so every reported W/L/PF is optimistic.
 H3 Wyckoff filter requires a NARROW high-volume bar for buys while the signal is a band BREAKOUT bar
    (usually wide): near-contradictory. Liquidity proximity default (2%) is a no-op on 1m-15m crypto.
MEDIUM
 M0 Bands can invert: ub = high - dn*ATR + k*ATR, lb = low + dn*ATR - k*ATR. When |dn| is large, lb > ub, both
    break conditions can fire together and the trend state (`cs` wins) contradicts the signal (`cb`).
    Measured on 20k synthetic random-walk 5m bars: inverted on 1.1% of bars but 4.1% of raw-signal bars;
    band_guard=True changes 96 of ~1,040 final signals. Real crypto volume is fatter-tailed: re-measure.
 M1 vp = volume*sign(close-open): crude, ignores wicks/close location, dojis = 0.
 M2 11 hard-coded fast/slow combos via nested ternaries; unsupported pairs silently fall back to 5/21.
 M3 z-score window of 20 bars on a signed-volume MACD: noisy; band offset (dn*ATR) moves with volume noise.
 M4 last_sig alternation updated before downstream filters; filtered signals are lost, not deferred.
LOW  table.new on every last-bar tick, tr shadows a built-in, mixed languages, duplicated headers,
     FIX-12 claim: scaling TP and SL by the same factor does not change R:R (it only widens both).
Evidence run on synthetic random-walk data (mechanism checks, NOT market statistics):
 • C2: original FVG logic created ~2,600 bull / ~2,700 bear gaps and had an 'active' zone on 0 bars.
 • C5: top-ranked of 132 combos on a 500-bar window: +0.97 R in-sample, -0.05 R on the next 500 bars (6 series).
 • Costs: zero-cost PF ~1.04, 5 bps fee + 2 bps slippage per side turns it into PF ~0.58.
Verdict: parameter-heavy, price/volume-only system with no independent information source and an
in-script optimizer that manufactures backtest winners. Treat any edge as UNPROVEN until it survives
walk-forward with costs (see walk_forward()).

────────────────────────── WHAT THIS ENGINE DOES ──────────────────────────
Signals computed on CLOSED bars; orders fill at the NEXT bar open (+ slippage); SL/TP are frozen at
entry from the signal-bar ATR; fees per side; optional opposite-signal handling; ATR-risk or fixed-%
sizing; buy&hold comparison; walk-forward helper; cost-sensitivity helper.

Fixes applied vs v4.4 (all other logic is faithful):
  C1 closed-bar only • C2 FVG rewritten (zone stays active until closed through or aged out)
  C4 frozen TP/SL • H1 lower timeframes than the chart are ignored • H2 costs modelled
  M2 combo is an explicit choice • band_guard (default False = faithful) optionally blocks flips
  while bands are inverted (M0)
Optimizer removed on purpose (C5): use walk_forward().

Requirements: Python 3.10+, numpy, pandas.
Data: DataFrame/CSV/Parquet with a UTC DatetimeIndex (bar OPEN time) and columns
      open, high, low, close, volume (Binance USDT-M klines work as-is).
CLI:  python sax_v4_engine.py --data BTCUSDT_5m.csv --fee-bps 5 --slippage-bps 2
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from dataclasses import asdict, dataclass, replace
from typing import Optional

import numpy as np
import pandas as pd

DRIFT_COMBOS = {
    "F3S13": (3, 13), "F3S21": (3, 21), "F3S34": (3, 34),
    "F5S13": (5, 13), "F5S21": (5, 21), "F5S34": (5, 34),
    "F8S13": (8, 13), "F8S21": (8, 21), "F8S34": (8, 34),
    "F13S21": (13, 21), "F13S34": (13, 34),
}


# ═════════════════════════════════ configuration ═════════════════════════════════
@dataclass
class SAXParams:
    # engine
    drift_combo: str = "F3S13"
    norm_len: int = 20
    atr_len: int = 14
    atr_mult: float = 1.2
    tp_mult: float = 3.0
    sl_mult: float = 1.2
    crypto_mode: bool = True
    crypto_scale: float = 1.4
    band_guard: bool = False          # False = faithful to v4.4 (bands may invert)
    # cooldown
    use_cooldown: bool = True
    cooldown_bars: int = 10
    # MTF
    use_mtf_gate: bool = True
    mtf_mode: str = "Suavizado"       # "Suavizado" | "Binario"
    mtf_min_bull: int = 4
    mtf_max_bull: int = 4
    mtf_score_thr: float = 0.25
    use_hard_floor: bool = True
    hard_floor_buy: int = 2
    hard_floor_sell: int = 2
    mtf_tfs: tuple = ("1", "3", "5", "15", "30", "60", "240", "D")
    # SMC
    use_fvg_filter: bool = False
    fvg_max_age: int = 50
    use_liquidity: bool = False
    liq_lookback: int = 20
    liq_proximity: float = 1.02
    use_wyckoff: bool = False
    wyckoff_vol_spike: float = 1.5
    wyckoff_absorb_pct: float = 0.7
    wyckoff_dist_pct: float = 1.5


@dataclass
class BacktestConfig:
    initial_capital: float = 10_000.0
    fee_bps: float = 5.0              # per side (0.05% = Binance USDT-M taker, standard tier)
    slippage_bps: float = 0.5         # per side, measured live 2026-10-25 (was 2.0)
    sizing_mode: str = "fixed_pct"    # "fixed_pct" | "atr_risk"
    pct_equity: float = 100.0
    risk_pct: float = 1.0
    max_leverage: float = 1.0
    opposite_signal: str = "ignore"   # "ignore" (v4.4 sim) | "close" | "reverse"
    allow_long: bool = True
    allow_short: bool = True
    both_hit_rule: str = "sl_first"   # when SL and TP are both inside one bar
    start: Optional[str] = None       # inclusive, e.g. "2025-01-01"
    end: Optional[str] = None


# ═════════════════════════════════ data helpers ═════════════════════════════════
def load_ohlcv(path: str) -> pd.DataFrame:
    """CSV/Parquet -> UTC DatetimeIndex (bar open) with open/high/low/close/volume."""
    df = pd.read_parquet(path) if path.lower().endswith((".parquet", ".pq")) else pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    tcol = next((c for c in ("open_time", "timestamp", "time", "datetime", "date") if c in df.columns), None)
    if tcol is not None:
        ts = df[tcol]
        if pd.api.types.is_numeric_dtype(ts):
            unit = "ms" if ts.iloc[0] > 1e11 else "s"
            df.index = pd.to_datetime(ts, unit=unit, utc=True)
        else:
            df.index = pd.to_datetime(ts, utc=True)
    return prepare(df)


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame needs a DatetimeIndex (bar open time, UTC)")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df = df[~df.index.duplicated(keep="last")].sort_index()
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[["open", "high", "low", "close", "volume"]].dropna(subset=["open", "high", "low", "close"])


def base_seconds(df: pd.DataFrame) -> int:
    return int(round(df.index.to_series().diff().dropna().dt.total_seconds().median()))


# ═════════════════════════════════ indicators (Pine-exact) ═════════════════════════════════
def ema(x: pd.Series, n: int) -> pd.Series:
    """ta.ema: recursive, seeded with the first value."""
    return x.ewm(span=n, adjust=False).mean()


def rma(x: np.ndarray, n: int) -> np.ndarray:
    """ta.rma: seeded with the SMA of the first n values."""
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    out[n - 1] = np.mean(x[:n])
    for i in range(n, len(x)):
        out[i] = (out[i - 1] * (n - 1) + x[i]) / n
    return out


def atr(high, low, close, n: int) -> np.ndarray:
    prev_c = np.concatenate(([np.nan], close[:-1]))
    tr = np.maximum.reduce([high - low, np.abs(high - prev_c), np.abs(low - prev_c)])
    tr[0] = high[0] - low[0]
    return rma(tr, n)


def zscore(x: pd.Series, n: int) -> pd.Series:
    """(x - sma) / stdev(population); NaN until the window is full; 0 if stdev == 0."""
    mu = x.rolling(n).mean()
    sd = x.rolling(n).std(ddof=0)
    z = (x - mu) / sd
    return z.where(sd != 0.0, 0.0).where(sd.notna())


# ═════════════════════════════════ MTF ═════════════════════════════════
def _tf_rule(tf: str) -> tuple[str, int]:
    t = str(tf).strip().upper()
    if t.isdigit():
        return f"{int(t)}min", int(t) * 60
    if t in ("D", "1D"):
        return "1D", 86_400
    if t in ("W", "1W"):
        return "1W", 604_800
    raise ValueError(f"unsupported timeframe: {tf}")


def precompute_mtf(df: pd.DataFrame, tfs: tuple) -> dict:
    """Pine: request.security(tf, ta.ema(close,20)[1] / ema(close,50)[1], lookahead_on).
    Each base bar sees the last COMPLETED higher-timeframe bar. Timeframes below the chart's are dropped."""
    base = base_seconds(df)
    cols, used = [], []
    for tf in tfs:
        rule, secs = _tf_rule(tf)
        if secs < base:
            continue
        hc = df["close"].resample(rule, label="left", closed="left").last().dropna()
        e20 = ema(hc, 20).shift(1)
        e50 = ema(hc, 50).shift(1)
        trend = pd.Series(np.where(e20 > e50, 1, -1), index=hc.index)   # NaN compares False -> -1, like Pine
        cols.append(trend.reindex(df.index, method="ffill").fillna(-1).to_numpy())
        used.append(tf)
    mat = np.column_stack(cols) if cols else np.empty((len(df), 0))
    return {"matrix": mat, "tfs": used}


# ═════════════════════════════════ signal engine ═════════════════════════════════
def _band_machine(high, low, close, dn, atr_v, am_eff, band_guard):
    n = len(close)
    ub = np.full(n, np.nan)
    lb = np.full(n, np.nan)
    trend = np.zeros(n, dtype=np.int8)
    buy_raw = np.zeros(n, dtype=bool)
    sell_raw = np.zeros(n, dtype=bool)
    inverted = np.zeros(n, dtype=bool)
    tr_prev, last_sig = 0, 0
    for i in range(n):
        d, a = dn[i], atr_v[i]
        if np.isnan(d) or np.isnan(a):
            ur = lr = np.nan
        else:
            dsc = d * a
            ur = (high[i] - dsc) + a * am_eff
            lr = (low[i] + dsc) - a * am_eff
        ub_p = ub[i - 1] if i > 0 else np.nan
        lb_p = lb[i - 1] if i > 0 else np.nan
        c_p = close[i - 1] if i > 0 else np.nan
        if np.isnan(ur):
            ub[i] = np.nan
        elif np.isnan(ub_p):
            ub[i] = ur
        else:
            ub[i] = min(ur, ub_p) if c_p <= ub_p else ur
        if np.isnan(lr):
            lb[i] = np.nan
        elif np.isnan(lb_p):
            lb[i] = lr
        else:
            lb[i] = max(lr, lb_p) if c_p >= lb_p else lr
        both = not (np.isnan(ub_p) or np.isnan(lb_p))
        inverted[i] = both and ub_p < lb_p
        ok = (not band_guard) or (both and ub_p > lb_p)
        cb = (not np.isnan(ub_p)) and close[i] > ub_p and tr_prev != 1 and ok
        cs = (not np.isnan(lb_p)) and close[i] < lb_p and tr_prev != -1 and ok
        tr_i = -1 if cs else (1 if cb else tr_prev)
        rb = cb and (not np.isnan(d)) and d > 0
        rs = cs and (not np.isnan(d)) and d < 0
        b = rb and last_sig != 1
        s = rs and last_sig != -1
        if b:
            last_sig = 1
        if s:
            last_sig = -1
        buy_raw[i], sell_raw[i], trend[i] = b, s, tr_i
        tr_prev = tr_i
    return ub, lb, trend, buy_raw, sell_raw, inverted


def _fvg_zones(high, low, close, max_age):
    n = len(close)
    bull = np.zeros(n, dtype=bool)
    bear = np.zeros(n, dtype=bool)
    b_on, b_bot, b_born = False, np.nan, 0
    s_on, s_top, s_born = False, np.nan, 0
    for i in range(n):
        if i >= 2 and low[i] > high[i - 2]:
            b_on, b_bot, b_born = True, high[i - 2], i
        elif b_on and (close[i] < b_bot or i - b_born > max_age):
            b_on = False
        if i >= 2 and high[i] < low[i - 2]:
            s_on, s_top, s_born = True, low[i - 2], i
        elif s_on and (close[i] > s_top or i - s_born > max_age):
            s_on = False
        bull[i], bear[i] = b_on, s_on
    return bull, bear


def _final_signals(buy_raw, sell_raw, buy_gate, sell_gate, use_cd, cd_bars):
    n = len(buy_raw)
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    lbb = lsb = -10**9
    for i in range(n):
        b = buy_raw[i] and buy_gate[i] and (not use_cd or i - lbb >= cd_bars)
        s = sell_raw[i] and sell_gate[i] and (not use_cd or i - lsb >= cd_bars)
        if b:
            lbb = i
        if s:
            lsb = i
        buy[i], sell[i] = b, s
    return buy, sell


def generate_signals(df: pd.DataFrame, p: SAXParams, mtf: Optional[dict] = None) -> pd.DataFrame:
    """Causal signal generation: row i only uses bars <= i. A True at row i means 'signal confirmed
    at the CLOSE of bar i' (the order executes at the open of bar i+1)."""
    if p.drift_combo not in DRIFT_COMBOS:
        raise ValueError(f"drift_combo must be one of {list(DRIFT_COMBOS)}")
    o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    vp = pd.Series(v * np.where(c > o, 1.0, np.where(c < o, -1.0, 0.0)), index=df.index)
    fast, slow = DRIFT_COMBOS[p.drift_combo]
    drift = ema(vp, fast) - ema(vp, slow)
    dn = zscore(drift, p.norm_len).to_numpy()
    atr_v = atr(h, l, c, p.atr_len)

    scale = p.crypto_scale if p.crypto_mode else 1.0
    ub, lb, trend, buy_raw, sell_raw, inverted = _band_machine(h, l, c, dn, atr_v, p.atr_mult * scale, p.band_guard)

    # MTF consensus
    mtf = mtf if mtf is not None else precompute_mtf(df, p.mtf_tfs)
    mat = mtf["matrix"]
    n_valid = mat.shape[1]
    bull = (mat == 1).sum(axis=1) if n_valid else np.zeros(len(df), dtype=int)
    bear = n_valid - bull
    w = bull / n_valid if n_valid else np.full(len(df), 0.5)
    with np.errstate(invalid="ignore"):
        if (not p.use_mtf_gate) or n_valid == 0:
            buy_mtf = sell_mtf = np.ones(len(df), dtype=bool)
        elif p.mtf_mode == "Suavizado":
            buy_mtf = np.abs(dn) * w > p.mtf_score_thr
            sell_mtf = np.abs(dn) * (1.0 - w) > p.mtf_score_thr
        else:
            buy_mtf = bull >= p.mtf_min_bull
            sell_mtf = bull <= p.mtf_max_bull
        hf_buy = np.ones(len(df), dtype=bool) if (not p.use_hard_floor or n_valid == 0) else bull >= p.hard_floor_buy
        hf_sell = np.ones(len(df), dtype=bool) if (not p.use_hard_floor or n_valid == 0) else bear >= p.hard_floor_sell

    # SMC filters
    S = lambda a: pd.Series(a, index=df.index)
    if p.use_fvg_filter:
        fvg_b, fvg_s = _fvg_zones(h, l, c, p.fvg_max_age)
    else:
        fvg_b = fvg_s = np.ones(len(df), dtype=bool)
    if p.use_liquidity:
        hh = S(h).rolling(p.liq_lookback).max()
        ll = S(l).rolling(p.liq_lookback).min()
        sw_h = (S(h) == hh) & (S(h) > S(h).shift(1))
        sw_l = (S(l) == ll) & (S(l) < S(l).shift(1))
        near_h = S(h).where(sw_h).ffill()
        near_l = S(l).where(sw_l).ffill()
        liq_b = (near_l.isna() | (S(l) <= near_l * p.liq_proximity)).to_numpy()
        liq_s = (near_h.isna() | (S(h) >= near_h * (2.0 - p.liq_proximity))).to_numpy()
    else:
        liq_b = liq_s = np.ones(len(df), dtype=bool)
    if p.use_wyckoff:
        vol_ratio = S(v) / S(v).rolling(20).mean()
        spike = (vol_ratio > p.wyckoff_vol_spike).to_numpy()
        spread = S(h - l)
        avg_spread = spread.rolling(14).mean()
        absorb = ((spread < avg_spread * p.wyckoff_absorb_pct).to_numpy()) & spike
        distrib = ((spread > avg_spread * p.wyckoff_dist_pct).to_numpy()) & spike & (c < o)
        wy_b, wy_s = absorb, distrib
    else:
        wy_b = wy_s = np.ones(len(df), dtype=bool)

    buy_gate = hf_buy & buy_mtf & fvg_b & liq_b & wy_b
    sell_gate = hf_sell & sell_mtf & fvg_s & liq_s & wy_s
    buy, sell = _final_signals(buy_raw, sell_raw, buy_gate, sell_gate, p.use_cooldown, p.cooldown_bars)

    return pd.DataFrame({
        "dn": dn, "atr": atr_v, "ub": ub, "lb": lb, "trend": trend,
        "bands_inverted": inverted, "mtf_bull": bull, "mtf_valid": n_valid,
        "buy_raw": buy_raw, "sell_raw": sell_raw, "buy": buy, "sell": sell,
    }, index=df.index)


# ═════════════════════════════════ backtest engine ═════════════════════════════════
@dataclass
class BacktestResult:
    metrics: dict
    trades: pd.DataFrame
    equity: pd.Series
    signals: pd.DataFrame


def _metrics(eq: pd.Series, trades: pd.DataFrame, df: pd.DataFrame, cfg: BacktestConfig,
             i0: int, i1: int, exposure_bars: int, bars_per_year: float) -> dict:
    e = eq.iloc[i0:i1 + 1]
    ret = e.pct_change().dropna()
    total = e.iloc[-1] / e.iloc[0] - 1.0 if len(e) > 1 else 0.0
    dd = (e / e.cummax() - 1.0).min() if len(e) > 1 else 0.0
    bh = df["close"].iloc[i1] / df["close"].iloc[i0] - 1.0
    sd = ret.std(ddof=1)
    sharpe = float(ret.mean() / sd * math.sqrt(bars_per_year)) if sd and sd > 0 else float("nan")
    m = {"bars": int(i1 - i0 + 1), "net_return_pct": total * 100, "buy_hold_return_pct": bh * 100,
         "excess_vs_buy_hold_pct": (total - bh) * 100, "max_drawdown_pct": dd * 100,
         "sharpe_annualised": sharpe, "n_trades": int(len(trades)),
         "exposure_pct": exposure_bars / max(i1 - i0 + 1, 1) * 100}
    if len(trades):
        wins, losses = trades[trades.pnl > 0], trades[trades.pnl <= 0]
        gp, gl = wins.pnl.sum(), -losses.pnl.sum()
        m.update({
            "win_rate_pct": len(wins) / len(trades) * 100,
            "profit_factor": float(gp / gl) if gl > 0 else float("inf"),
            "avg_trade_pct": float(trades.pnl_pct.mean() * 100),
            "expectancy_R": float(trades.R.mean()),
            "avg_win_R": float(wins.R.mean()) if len(wins) else 0.0,
            "avg_loss_R": float(losses.R.mean()) if len(losses) else 0.0,
            "long_trades": int((trades.dir == 1).sum()), "short_trades": int((trades.dir == -1).sum()),
            "avg_bars_in_trade": float(trades.bars.mean()),
            "fees_paid": float(trades.fees.sum()),
            "gross_return_pct": float((trades.pnl + trades.fees).sum() / cfg.initial_capital * 100),
            "exit_reasons": trades.reason.value_counts().to_dict(),
        })
    else:
        m.update({"win_rate_pct": float("nan"), "profit_factor": float("nan")})
    return m


def backtest(df: pd.DataFrame, p: SAXParams, cfg: BacktestConfig,
             signals: Optional[pd.DataFrame] = None, bounds: Optional[tuple[int, int]] = None) -> BacktestResult:
    """Bar-by-bar simulation. `bounds=(i0, i1)` restricts trading to bar positions [i0, i1]
    (used by walk_forward); otherwise cfg.start/cfg.end are used."""
    sig = signals if signals is not None else generate_signals(df, p)
    n = len(df)
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    buy, sell, atr_v = sig["buy"].to_numpy(), sig["sell"].to_numpy(), sig["atr"].to_numpy()
    idx = df.index
    if bounds is not None:
        i0, i1 = bounds
    else:
        i0 = int(idx.searchsorted(pd.Timestamp(cfg.start, tz="UTC"), side="left")) if cfg.start else 0
        i1 = (int(idx.searchsorted(pd.Timestamp(cfg.end, tz="UTC"), side="right")) - 1) if cfg.end else n - 1
    i0, i1 = max(i0, 0), min(i1, n - 1)

    scale = p.crypto_scale if p.crypto_mode else 1.0
    sl_k, tp_k = p.sl_mult * scale, p.tp_mult * scale
    fee, slip = cfg.fee_bps / 1e4, cfg.slippage_bps / 1e4

    cash = cfg.initial_capital
    pos, qty, entry, sl, tp = 0, 0.0, np.nan, np.nan, np.nan
    entry_i, entry_fee, risk_amt = -1, 0.0, np.nan
    pending = None
    trades: list[dict] = []
    equity = np.full(n, np.nan)
    exposure = 0

    def close_pos(px: float, i: int, reason: str):
        nonlocal cash, pos, qty
        exit_fee = qty * px * fee
        gross = pos * qty * (px - entry)
        pnl = gross - exit_fee - entry_fee
        cash += gross - exit_fee
        trades.append({"entry_time": idx[entry_i], "exit_time": idx[i], "dir": pos, "entry": entry, "exit": px,
                       "qty": qty, "pnl": pnl, "pnl_pct": pnl / max(qty * entry, 1e-12),
                       "R": pnl / risk_amt if risk_amt and risk_amt > 0 else np.nan,
                       "bars": i - entry_i, "fees": entry_fee + exit_fee, "reason": reason})
        pos, qty = 0, 0.0

    for i in range(i0, i1 + 1):
        # 1) execute pending order at this bar's open
        if pending is not None:
            kind = pending["kind"]
            if kind in ("close", "reverse") and pos != 0:
                close_pos(o[i] * (1.0 - slip * pos), i, "opposite_signal")
            if kind in ("open", "reverse"):
                d = pending["dir"]
                px = o[i] * (1.0 + slip * d)
                entry_fee = pending["qty"] * px * fee
                cash -= entry_fee
                pos, qty, entry, entry_i = d, pending["qty"], px, i
                sl, tp = px - d * pending["sl_d"], px + d * pending["tp_d"]
                risk_amt = pending["qty"] * pending["sl_d"]
            pending = None

        # 2) intrabar SL/TP on the open position (including one opened at this bar's open)
        if pos != 0:
            if pos == 1:
                sl_open, tp_open = o[i] <= sl, o[i] >= tp
                sl_in, tp_in = l[i] <= sl, h[i] >= tp
            else:
                sl_open, tp_open = o[i] >= sl, o[i] <= tp
                sl_in, tp_in = h[i] >= sl, l[i] <= tp
            exit_kind = None
            if sl_open:
                exit_kind, fill = "sl", o[i]
            elif tp_open:
                exit_kind, fill = "tp", o[i]
            elif sl_in and tp_in:
                exit_kind = "sl" if cfg.both_hit_rule == "sl_first" else "tp"
                fill = sl if exit_kind == "sl" else tp
            elif sl_in:
                exit_kind, fill = "sl", sl
            elif tp_in:
                exit_kind, fill = "tp", tp
            if exit_kind == "sl":
                close_pos(fill * (1.0 - slip * pos), i, "sl")     # stop-market: adverse slippage
            elif exit_kind == "tp":
                close_pos(fill, i, "tp")                          # limit: no slippage

        # 3) mark-to-market at the close
        equity[i] = cash + (pos * qty * (c[i] - entry) if pos != 0 else 0.0)
        if pos != 0:
            exposure += 1

        # 4) signals confirmed at this close -> order for the next open
        if i < i1 and not np.isnan(atr_v[i]) and atr_v[i] > 0:
            want = 1 if buy[i] else (-1 if sell[i] else 0)
            if want != 0:
                allowed = cfg.allow_long if want == 1 else cfg.allow_short
                sl_d, tp_d = atr_v[i] * sl_k, atr_v[i] * tp_k
                eq = equity[i]
                if cfg.sizing_mode == "atr_risk":
                    q = eq * cfg.risk_pct / 100.0 / sl_d
                else:
                    q = eq * cfg.pct_equity / 100.0 / c[i]
                q = min(q, eq * cfg.max_leverage / c[i])
                new = {"kind": "open", "dir": want, "qty": q, "sl_d": sl_d, "tp_d": tp_d}
                if pos == 0:
                    if allowed and q > 0:
                        pending = new
                elif pos != want and cfg.opposite_signal != "ignore":
                    if cfg.opposite_signal == "reverse" and allowed and q > 0:
                        new["kind"] = "reverse"
                        pending = new
                    else:
                        pending = {"kind": "close"}

    if pos != 0:                                    # mark the final open trade to the last close
        close_pos(c[i1] * (1.0 - slip * pos), i1, "end_of_data")
        equity[i1] = cash

    eq_s = pd.Series(equity, index=idx).ffill()
    tdf = pd.DataFrame(trades)
    if tdf.empty:
        tdf = pd.DataFrame(columns=["entry_time", "exit_time", "dir", "entry", "exit", "qty", "pnl", "pnl_pct",
                                    "R", "bars", "fees", "reason"])
    bpy = 365.0 * 86400.0 / base_seconds(df)
    return BacktestResult(_metrics(eq_s, tdf, df, cfg, i0, i1, exposure, bpy), tdf, eq_s, sig)


# ═════════════════════════════════ research helpers ═════════════════════════════════
def cost_sensitivity(df: pd.DataFrame, p: SAXParams, cfg: BacktestConfig,
                     fee_grid=(0.0, 2.0, 5.0, 8.0), slip_grid=(0.0, 2.0, 5.0)) -> pd.DataFrame:
    """Net return across fee/slippage assumptions (signals computed once)."""
    sig = generate_signals(df, p)
    rows = []
    for f, s in itertools.product(fee_grid, slip_grid):
        r = backtest(df, p, replace(cfg, fee_bps=f, slippage_bps=s), signals=sig)
        rows.append({"fee_bps": f, "slippage_bps": s, "net_return_pct": r.metrics["net_return_pct"],
                     "profit_factor": r.metrics.get("profit_factor"), "n_trades": r.metrics["n_trades"]})
    return pd.DataFrame(rows)


def walk_forward(df: pd.DataFrame, base: SAXParams, grid: dict, cfg: BacktestConfig,
                 train_bars: int, test_bars: int, objective: str = "sharpe_annualised",
                 min_trades: int = 30, max_combos: int = 60) -> dict:
    """Rolling walk-forward: pick the best grid point on each train window (objective metric, min_trades),
    then trade it, untouched, on the next test window. Signals are causal, so they are computed once per
    combo over the whole series (no leakage). Returns per-fold table + out-of-sample summary."""
    keys = list(grid)
    combos = list(itertools.product(*[grid[k] for k in keys]))
    if len(combos) > max_combos:
        raise ValueError(f"{len(combos)} combos > max_combos={max_combos}: shrink the grid "
                         "(every extra combo raises the odds of a lucky winner)")
    mtf = precompute_mtf(df, base.mtf_tfs)
    sigs = {cmb: generate_signals(df, replace(base, **dict(zip(keys, cmb))), mtf) for cmb in combos}
    folds, i = [], 0
    n = len(df)
    start = 0
    while start + train_bars + test_bars <= n:
        tr, te = (start, start + train_bars - 1), (start + train_bars, start + train_bars + test_bars - 1)
        best, best_val, best_train = None, -np.inf, None
        for cmb in combos:
            r = backtest(df, replace(base, **dict(zip(keys, cmb))), cfg, signals=sigs[cmb], bounds=tr)
            val = r.metrics.get(objective, float("nan"))
            if r.metrics["n_trades"] >= min_trades and np.isfinite(val) and val > best_val:
                best, best_val, best_train = cmb, val, r.metrics
        if best is None:
            folds.append({"fold": i, "params": None, "train_obj": np.nan, "test_net_return_pct": 0.0,
                          "test_buy_hold_pct": np.nan, "test_trades": 0})
        else:
            rt = backtest(df, replace(base, **dict(zip(keys, best))), cfg, signals=sigs[best], bounds=te)
            folds.append({"fold": i, "params": dict(zip(keys, best)), "train_obj": best_val,
                          "train_net_return_pct": best_train["net_return_pct"],
                          "test_net_return_pct": rt.metrics["net_return_pct"],
                          "test_buy_hold_pct": rt.metrics["buy_hold_return_pct"],
                          "test_trades": rt.metrics["n_trades"],
                          "test_profit_factor": rt.metrics.get("profit_factor")})
        i += 1
        start += test_bars
    tab = pd.DataFrame(folds)
    oos = float(np.prod(1 + tab["test_net_return_pct"].fillna(0) / 100.0) - 1) * 100 if len(tab) else float("nan")
    summary = {"folds": int(len(tab)), "oos_compounded_net_return_pct": oos,
               "folds_profitable": int((tab["test_net_return_pct"] > 0).sum()) if len(tab) else 0,
               "mean_train_net_return_pct": float(tab.get("train_net_return_pct", pd.Series(dtype=float)).mean()),
               "mean_test_net_return_pct": float(tab["test_net_return_pct"].mean()) if len(tab) else float("nan")}
    return {"folds": tab, "summary": summary}


WHY_IT_COULD_STOP_WORKING = [
    "Price/volume-only inputs: no information source independent of what every other TA system sees.",
    "Parameter surface is large (combo, bands, TP/SL, MTF thresholds, cooldown, filters): any in-sample winner is probably noise.",
    "Signed-volume proxy (volume x candle colour) changes meaning across exchanges, listings and regimes.",
    "Cost drag: tight ATR stops on 1m-15m mean fees + slippage consume a large share of each R.",
    "Regime dependence: band-break systems earn in trends and bleed in ranges; MTF consensus lags regime changes.",
    "Execution gap: the simulator assumes next-open fills and an SL-first tie rule; live queueing, latency and funding differ.",
]


def format_report(res: BacktestResult, label: str = "SAX v4 (audited)") -> str:
    m = res.metrics
    lines = [f"=== {label} ===",
             f"bars {m['bars']:,} | trades {m['n_trades']} (L {m.get('long_trades', 0)} / S {m.get('short_trades', 0)}) | exposure {m['exposure_pct']:.1f}%",
             f"net return {m['net_return_pct']:.2f}% | buy&hold {m['buy_hold_return_pct']:.2f}% | excess {m['excess_vs_buy_hold_pct']:.2f}%",
             f"max drawdown {m['max_drawdown_pct']:.2f}% | sharpe {m['sharpe_annualised']:.2f}"]
    if m["n_trades"]:
        lines += [f"win rate {m['win_rate_pct']:.1f}% | profit factor {m['profit_factor']:.2f} | expectancy {m['expectancy_R']:.3f} R | avg trade {m['avg_trade_pct']:.3f}%",
                  f"gross return {m['gross_return_pct']:.2f}% vs net {m['net_return_pct']:.2f}% (fees {m['fees_paid']:.2f}) | exits {m['exit_reasons']}"]
    lines += ["", "WHY THIS COULD STOP WORKING"] + [f" - {x}" for x in WHY_IT_COULD_STOP_WORKING]
    return "\n".join(lines)


# Spec for the research pipeline / optimisers (kept small on purpose)
STRATEGY_SPEC = {
    "name": "SAX_v4_audited", "version": "4.4-audited", "engine": "sax_v4_engine.py",
    "pine": "SAX_v4_strategy.pine", "data": "OHLCV UTC bar-open index; volume required",
    "params": asdict(SAXParams()), "backtest_defaults": asdict(BacktestConfig()),
    "suggested_grid": {"drift_combo": ["F3S13", "F5S21", "F8S34"], "tp_mult": [2.0, 3.0, 4.0],
                       "sl_mult": [1.0, 1.2, 1.6], "mtf_mode": ["Suavizado", "Binario"]},
    "rules": ["closed-bar signals", "next-open fills", "frozen ATR TP/SL at entry",
              "no look-ahead", "fees+slippage always on", "walk-forward before any claim"],
}


# ═════════════════════════════════ CLI ═════════════════════════════════
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True)
    ap.add_argument("--fee-bps", type=float, default=5.0)
    ap.add_argument("--slippage-bps", type=float, default=2.0)
    ap.add_argument("--sizing", choices=["fixed_pct", "atr_risk"], default="fixed_pct")
    ap.add_argument("--opposite", choices=["ignore", "close", "reverse"], default="ignore")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--combo", default="F3S13", choices=list(DRIFT_COMBOS))
    ap.add_argument("--band-guard", action="store_true")
    ap.add_argument("--costs", action="store_true", help="also print the cost-sensitivity table")
    ap.add_argument("--json", action="store_true", help="print metrics as JSON only")
    a = ap.parse_args()
    df = load_ohlcv(a.data)
    p = SAXParams(drift_combo=a.combo, band_guard=a.band_guard)
    cfg = BacktestConfig(fee_bps=a.fee_bps, slippage_bps=a.slippage_bps, sizing_mode=a.sizing,
                         opposite_signal=a.opposite, start=a.start, end=a.end)
    res = backtest(df, p, cfg)
    if a.json:
        print(json.dumps(res.metrics, default=str, indent=2))
        return
    print(format_report(res))
    inv = res.signals["bands_inverted"].mean() * 100
    print(f"\nbands inverted on {inv:.1f}% of bars (audit C3)")
    if a.costs:
        print("\n" + cost_sensitivity(df, p, cfg).to_string(index=False))


if __name__ == "__main__":
    main()
