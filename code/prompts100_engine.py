"""Formal validation engine for the 5 survivors of the prompts-100 screen.

Provenance: the strategies and the event motor are faithful ports of
trading-engines/backtest_prompts100/ (strategies.py s28/s44/s60/s71/s73 +
btlib.py run_engine/evaluate), frozen here so REGLA 0 applies to them: the
screen numbers were console/pkl output; these runs produce hashed artifacts.

Conventions carried over from the screen (and the source document):
- signal on bar close, fill at next bar open
- the stop wins ties (if low<=stop and high>=target, the stop exits first)
- 1% of equity risked per trade from the ATR stop distance
- costs: 11 bps round trip (5 fee + 0.5 slippage per side, repo 2026-10-25)
- 70/30 IS/OOS split by bar count; gates: PF>1.2, n>=30, net>0 (full and OOS)
- no funding: none of the five is a funding strategy in the screen

The five are registry-bound to their screen symbol and timeframe; the adapter
refuses any other combination. Parameters are frozen from the prompts -- there
is no fitting anywhere in this file, so the purged-split rules of G3 have
nothing to leak.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

STRATEGY_SYMBOLS = {
    28: "BTCUSDT",   # Donchian breakout
    44: "BTCUSDT",   # 168-bar breakout
    60: "HYPEUSDT",  # Keltner con RSI
    71: "JUPUSDT",   # Hour-of-day filter
    73: "ETHUSDT",   # Sunday-to-Monday reversion
}

STRATEGY_NAMES = {
    28: "Donchian breakout",
    44: "168-bar breakout",
    60: "Keltner con RSI",
    71: "Hour-of-day filter",
    73: "Sunday-to-Monday reversion",
}

BARS_PER_YEAR = {"1h": 8760, "15m": 35040, "5m": 105120}


# ---------------------------------------------------------------- indicators
# Ported byte-faithful from btlib.py: same formulas, same pandas calls, same
# min_periods. These five strategies only use the subset below.

def ts_of(df):
    return pd.to_datetime(df["open_ts"], unit="ms", utc=True)


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0.0)
    dn = (-d).clip(lower=0.0)
    ru = up.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rd = dn.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = ru / rd.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def true_range(df):
    pc = df["close"].shift(1)
    return pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(),
                      (df["low"] - pc).abs()], axis=1).max(axis=1)


def atr(df, n=14):
    return true_range(df).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def keltner(df, n=20, m=1.5):
    mid = ema(df["close"], n)
    a = atr(df, n)
    return mid + m * a, mid, mid - m * a


def donchian(df, n):
    return df["high"].rolling(n).max(), df["low"].rolling(n).min()


def cross_up(a, b):
    return (a > b) & (a.shift(1) <= b.shift(1))


def cross_dn(a, b):
    return (a < b) & (a.shift(1) >= b.shift(1))


def SIG(df, le=None, se=None, lx=None, sx=None, sd=None, **kw):
    n = len(df)
    z = np.zeros(n, bool)
    d = dict(long_entry=le if le is not None else z,
             short_entry=se if se is not None else z,
             long_exit=lx if lx is not None else z.copy(),
             short_exit=sx if sx is not None else z.copy(),
             stop_dist=sd if sd is not None else np.zeros(n))
    d.update(kw)
    return d


# ---------------------------------------------------------------- strategies
# Bodies ported verbatim from backtest_prompts100/strategies.py.

def s28(df):
    hh, ll = donchian(df, 55)
    _, ll20 = donchian(df, 20)
    a = atr(df, 14)
    return SIG(df, le=df["close"] > hh.shift(1), lx=df["close"] < ll20.shift(1),
               sd=3 * a)


def s44(df):
    hh = df["high"].rolling(168).max()
    ll = df["low"].rolling(72).min()
    a = atr(df, 14)
    return SIG(df, le=df["close"] > hh.shift(1), lx=df["close"] < ll.shift(1), sd=2.5 * a)


def s60(df):
    up, mid, lo = keltner(df, 20, 2)
    r = rsi(df["close"], 14)
    e20 = ema(df["close"], 20)
    a = atr(df, 14)
    return SIG(df, le=(df["close"] > up) & (r > 60), lx=df["close"] < e20, sd=2 * a)


def s71(df):
    ts = ts_of(df)
    e20, e50 = ema(df["close"], 20), ema(df["close"], 50)
    a = atr(df, 14)
    win = ts.dt.hour.isin([14, 15, 16, 17])
    return SIG(df, le=cross_up(e20, e50) & win, se=cross_dn(e20, e50) & win,
               lx=cross_dn(e20, e50), sx=cross_up(e20, e50), sd=2 * a)


def s73(df):
    ts = ts_of(df)
    a = atr(df, 14)
    sun = ts.dt.dayofweek == 6
    sun_open = df["open"].where(sun & (ts.dt.hour == 0)).groupby(
        ts.dt.strftime("%Y-%m-%d")).transform("first")
    sun_ret = df["close"] - sun_open
    le = sun & (ts.dt.hour == 23) & (sun_ret < -a)
    mon23 = (ts.dt.dayofweek == 0) & (ts.dt.hour == 23)
    tue0 = (ts.dt.dayofweek == 1) & (ts.dt.hour == 0)
    lx = mon23 | tue0
    return SIG(df, le=le, lx=lx, sd=2 * a)


STRATEGIES = {28: s28, 44: s44, 60: s60, 71: s71, 73: s73}


# ---------------------------------------------------------------- event motor
# Port of btlib.run_engine for the subset these five use: entry/exit signals
# and a fixed ATR stop. No targets, trailing, max_bars or funding (none of the
# five used them in the screen; the branches are omitted, not approximated).

def run_engine(df, sig, cost_rt=0.0011, risk=0.01):
    o = df["open"].values
    h = df["high"].values
    l = df["low"].values
    c = df["close"].values
    n = len(df)
    long_entry = np.asarray(sig["long_entry"], dtype=bool)
    short_entry = np.asarray(sig["short_entry"], dtype=bool)
    long_exit = np.asarray(sig["long_exit"], dtype=bool)
    short_exit = np.asarray(sig["short_exit"], dtype=bool)
    stop_d = np.asarray(sig["stop_dist"], dtype=float)

    pos = 0.0
    entry = stop = 0.0
    d0 = 1.0
    entry_i = -1
    entry_px = 0.0
    realized = 1.0
    eq_curve = np.ones(n)
    trades = []

    for i in range(n):
        if pos > 0:
            exit_px = None
            if long_exit[i - 1] if i >= 1 else False:
                exit_px = o[i]
            elif l[i] <= stop:
                exit_px = min(o[i], stop)
            if exit_px is not None:
                r = (exit_px - entry) / d0 - cost_rt * abs(entry_px) / d0
                realized *= (1 + risk * r)
                trades.append(dict(entry_i=entry_i, exit_i=i, dir=1, r=r))
                pos = 0.0
        elif pos < 0:
            exit_px = None
            if short_exit[i - 1] if i >= 1 else False:
                exit_px = o[i]
            elif h[i] >= stop:
                exit_px = max(o[i], stop)
            if exit_px is not None:
                r = (entry - exit_px) / d0 - cost_rt * abs(entry_px) / d0
                realized *= (1 + risk * r)
                trades.append(dict(entry_i=entry_i, exit_i=i, dir=-1, r=r))
                pos = 0.0

        if pos == 0 and i >= 1:
            if long_entry[i - 1] and stop_d[i - 1] > 0:
                pos = 1.0
                entry = o[i]
                entry_px = o[i]
                d0 = stop_d[i - 1]
                entry_i = i
                stop = entry - d0
                if l[i] <= stop:  # stop puede saltar en la propia barra de entrada
                    r = (min(o[i], stop) - entry) / d0 - cost_rt * abs(entry_px) / d0
                    realized *= (1 + risk * r)
                    trades.append(dict(entry_i=entry_i, exit_i=i, dir=1, r=r))
                    pos = 0.0
            elif short_entry[i - 1] and stop_d[i - 1] > 0:
                pos = -1.0
                entry = o[i]
                entry_px = o[i]
                d0 = stop_d[i - 1]
                entry_i = i
                stop = entry + d0
                if h[i] >= stop:
                    r = (entry - max(o[i], stop)) / d0 - cost_rt * abs(entry_px) / d0
                    realized *= (1 + risk * r)
                    trades.append(dict(entry_i=entry_i, exit_i=i, dir=-1, r=r))
                    pos = 0.0

        if pos > 0:
            unreal = (c[i] - entry) / d0 - cost_rt * abs(entry_px) / d0
            eq_curve[i] = realized * (1 + risk * unreal)
        elif pos < 0:
            unreal = (entry - c[i]) / d0 - cost_rt * abs(entry_px) / d0
            eq_curve[i] = realized * (1 + risk * unreal)
        else:
            eq_curve[i] = realized

    if pos != 0:  # cerrar al final
        exit_px = c[-1]
        if pos > 0:
            r = (exit_px - entry) / d0 - cost_rt * abs(entry_px) / d0
        else:
            r = (entry - exit_px) / d0 - cost_rt * abs(entry_px) / d0
        realized *= (1 + risk * r)
        trades.append(dict(entry_i=entry_i, exit_i=n - 1, dir=int(pos), r=r))
        eq_curve[-1] = realized
    return eq_curve, trades


# ---------------------------------------------------------------- metrics
def max_drawdown(eq):
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1).min())


def sharpe(eq, bars_per_year):
    r = np.diff(eq) / eq[:-1]
    r = r[np.isfinite(r)]
    if len(r) < 2 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(bars_per_year))


def pf_winrate(trades):
    rs = np.array([t["r"] for t in trades]) if trades else np.array([])
    if len(rs) == 0:
        return 0.0, 0.0, 0.0
    gp = rs[rs > 0].sum()
    gl = -rs[rs < 0].sum()
    pf = gp / gl if gl > 0 else (np.inf if gp > 0 else 0.0)
    return float(pf), float((rs > 0).mean()), float(rs.sum())


def segment_stats(eq, trades, i0, i1, bars_per_year):
    seg = eq[i0:i1]
    seg_tr = [t for t in trades if i0 <= t["entry_i"] < i1]
    net = float(seg[-1] / seg[0] - 1) if len(seg) > 1 else 0.0
    pf, wr, _ = pf_winrate(seg_tr)
    return dict(net=net, mdd=max_drawdown(seg), pf=pf, wr=wr, n=len(seg_tr),
                sharpe=sharpe(seg, bars_per_year))


# ---------------------------------------------------------------- entry point
def run(paths, params):
    p = dict(params)
    _tf = p.pop("tf")
    sid = int(p.pop("id"))
    fee = float(p.pop("fee_bps", 5.0))       # repo 2026-10-25: 5+0.5 = 11 bps RT
    slip = float(p.pop("slippage_bps", 0.5))
    risk = float(p.pop("risk", 0.01))
    split_frac = float(p.pop("split_frac", 0.7))
    if _tf != "1h":
        raise ValueError(f"prompts100 survivors are 1h strategies, got tf={_tf!r}")
    if p:
        raise ValueError(f"unknown prompts100 params: {sorted(p)}")

    frames = []
    for path in paths:
        raw = pd.read_csv(path)
        frames.append(raw[["open_ts", "open", "high", "low", "close", "volume"]].astype(float))
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates("open_ts").sort_values("open_ts").reset_index(drop=True)
    # the screen built signals on the df and index-aligned arrays; restore that
    ts = ts_of(df)
    df.index = pd.RangeIndex(len(df))
    if len(df) < 1000:
        raise ValueError(f"only {len(df)} bars -- not enough to test")

    fn = STRATEGIES[sid]
    sig = fn(df)
    cost_rt = 2.0 * (fee + slip) / 10000.0
    bpy = BARS_PER_YEAR[_tf]

    eq, trades = run_engine(df, sig, cost_rt=cost_rt, risk=risk)
    n = len(df)
    split = int(n * split_frac)
    full = segment_stats(eq, trades, 0, n, bpy)
    is_ = segment_stats(eq, trades, 0, split, bpy)
    oos = segment_stats(eq, trades, split, n, bpy)
    c0, cs, c1 = df["close"].iloc[0], df["close"].iloc[split], df["close"].iloc[-1]
    bh_full = float(c1 / c0 - 1)
    bh_oos = float(c1 / cs - 1)
    oos["excess"] = float(oos["net"] - bh_oos)
    full["excess"] = float(full["net"] - bh_full)
    is_["excess"] = float(is_["net"] - (df["close"].iloc[split] / c0 - 1))
    gate = bool(full["pf"] > 1.2 and full["n"] >= 30 and full["net"] > 0)
    oos_ok = bool(oos["pf"] > 1.2 and oos["net"] > 0 and oos["n"] >= 30)

    # concentration diagnostic (cbpackf convention): share of total trade PnL
    # held by the best 5 trades, and the PF without them.
    rs = np.array([t["r"] for t in trades])
    top5_share = float(np.sort(rs)[-5:].sum() / rs.sum()) if len(rs) >= 5 and rs.sum() > 0 else None
    rs_wo5 = np.sort(rs)[:-5] if len(rs) > 5 else rs
    gp, gl = rs_wo5[rs_wo5 > 0].sum(), -rs_wo5[rs_wo5 < 0].sum()
    pf_wo5 = float(gp / gl) if gl > 0 else None

    # exit-month net buckets (G4-style reading, not the gate itself)
    ex_ts = ts[[t["exit_i"] for t in trades]]
    months = pd.Series([f"{d.year:04d}-{d.month:02d}" for d in ex_ts])
    r_eq = np.array([risk * t["r"] for t in trades])
    bucket = {}
    for m in sorted(months.unique()):
        sel = np.array(months == m)
        seg_r = 1.0 + r_eq[sel]
        bucket[m] = float(seg_r.prod() - 1.0)
    green = sum(1 for v in bucket.values() if v > 0)

    times = ts.values
    trade_rows = [
        {"entry": str(pd.Timestamp(times[t["entry_i"]])),
         "exit": str(pd.Timestamp(times[t["exit_i"]])),
         "dir": t["dir"], "r": t["r"]}
        for t in trades
    ]

    # percent-form mirrors of the segment stats, so reports can quote the same
    # units the artifact stores (guard matches numbers at stored precision)
    def _pct(seg, bh):
        return {"net_pct": seg["net"] * 100.0, "mdd_pct": seg["mdd"] * 100.0,
                "excess_pct": seg["excess"] * 100.0, "bh_pct": bh * 100.0}

    name = STRATEGY_NAMES[sid]
    metrics = {
        "strategy_id": sid,
        "strategy_name": name,
        "expected_symbol": STRATEGY_SYMBOLS[sid],
        "bars": int(n),
        "window_utc": [str(pd.Timestamp(times[0])), str(pd.Timestamp(times[-1]))],
        "split_bar": int(split),
        "cost_bp_roundtrip": 2.0 * (fee + slip),
        "fee_bps_per_side": fee, "slippage_bps_per_side": slip,
        "risk_per_trade": risk,
        "full": full, "is": is_, "oos": oos,
        "full_pct": _pct(full, bh_full), "is_pct": _pct(is_, df["close"].iloc[split] / c0 - 1),
        "oos_pct": _pct(oos, bh_oos),
        "bh_full": bh_full, "bh_oos": bh_oos,
        "gate_full": gate, "gate_oos": oos_ok,
        "top5_pnl_share": top5_share,
        "pf_wo_top5": pf_wo5,
        "exit_month_buckets": bucket,
        "green_month_frac": (green / len(bucket)) if bucket else None,
        "n_exit_months": len(bucket),
        "worst_month_pct": (min(bucket.values()) * 100.0) if bucket else None,
    }
    prov = {
        "adapter": "prompts100", "engine_version": "prompts100-1",
        "source_file": "trading-engines/backtest_prompts100/strategies.py (s%d)" % sid,
        "conventions": ["signal close / fill next open", "stop wins ties",
                        "1% risk per ATR stop", "70/30 IS-OOS by bars"],
        "costs": {"fee_bps": fee, "slippage_bps": slip},
        "funding_charged": False,
        "pre_registered": False,
    }
    tables = [
        {"kind": "summary", "id": sid, "name": name,
         "trades": full["n"], "pf": full["pf"], "net_%": full["net"] * 100.0,
         "oos_trades": oos["n"], "oos_pf": oos["pf"], "oos_net_%": oos["net"] * 100.0,
         "gate": gate, "oos_ok": oos_ok},
        {"kind": "trades", "rows": trade_rows},
    ]
    return metrics, prov, tables
