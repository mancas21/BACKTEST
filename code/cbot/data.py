"""data -- loaders for real Binance data, plus the synthetic known-answer worlds.

REAL DATA
    load_or_fetch reads the 5m CSVs written by `fetch_5m_taker.py`, which keep
    Binance kline fields 5 (volume) and 9 (taker_buy_base). Those two are what
    S05 (taker-flow imbalance) and S06 (CVD divergence) need; without field 9
    those strategies cannot be tested at all rather than tested badly.

SYNTHETIC WORLDS
    The pack's own validation design: each world plants ONE effect, so a
    correctly built suite must find THAT strategy and no other. `null` plants
    nothing and must produce zero passes at any cost level. This is a
    known-answer test of the ENGINE -- it says nothing about real markets, and
    the pack itself labels it "SYNTHETIC".

    The generator is deliberately simple: a GBM price path whose drift/carry is
    modulated by the planted effect, with a taker-flow series that is predictive
    only in the `flow` world.
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
D5T = os.path.join(ROOT, "data", "binance_klines_5m_taker")

WORLDS = ["null", "momentum", "meanrev", "flow", "season", "volshock", "regime_ac"]


def load_or_fetch(symbol: str, interval: str, days: int, cache: str | None = None) -> pd.DataFrame:
    """Read the local 5m taker CSV. `days` trims the window; `cache` is accepted
    for signature compatibility with the pack's CLI."""
    path = os.path.join(D5T, f"{symbol}_5m.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found -- run code/fetch_5m_taker.py first "
            f"(it needs the taker_buy_base field that the older CSVs dropped)")
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    ts = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
    df = df.set_index(ts)
    keep = ["open", "high", "low", "close", "volume", "taker_buy_base"]
    df = df[keep].astype(float)
    if days:
        cut = df.index[-1] - pd.Timedelta(days=days)
        df = df[df.index >= cut]
    if len(df) < 1000:
        raise ValueError(f"only {len(df)} bars for {symbol} -- not enough to test")
    return df


def make_world(name: str, a: float = 0.2, n: int = 30000, seed: int = 42) -> pd.DataFrame:
    """One planted effect per world -- a KNOWN-ANSWER test of the engine.

    This generator is NOT the pack's (theirs is not in the archive), so it
    validates that the engine can detect an effect that is definitely there, and
    that it reports nothing when nothing is there. It cannot reproduce their
    published gross t-statistics and does not claim to.

    `a` scales every planted effect. At a=0.2 the effects are deliberately near
    the detection floor; the validation run uses a=1.0 so a failure is a bug
    rather than a power problem.
    """
    rng = np.random.default_rng(seed)
    bars_per_day = 24 * 12
    # 1.1% DAILY vol, converted to a per-5m-bar figure by dividing by sqrt(bars).
    # The original multiplied and left sig at 1.1% per bar (~19% daily), which
    # made every synthetic path wander over 3 orders of magnitude.
    sig = 0.011 / np.sqrt(bars_per_day)
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    # Effects scale off `a` but the AUTOREGRESSIVE coefficient must stay < 1 or
    # the path explodes: with k = a/0.2 and a=1.0 the original coefficient was
    # 1.75, a non-stationary AR(1) that drove close to inf, made sig all-NaN,
    # and produced a backtest with 0 trades and t_stat = nan. Bounded here.
    k = a / 0.2
    ac = min(0.45 * a, 0.55)                 # |ac| < 1 by construction

    if name == "momentum":
        r = np.zeros(n)
        for i in range(1, n):
            r[i] = sig * rng.standard_normal() + ac * r[i - 1]
    elif name == "meanrev":
        r = np.zeros(n)
        for i in range(1, n):
            r[i] = sig * rng.standard_normal() - ac * r[i - 1]
    elif name == "regime_ac":
        blk = np.repeat(rng.choice([-1.0, 1.0], size=n // 2000 + 2), 2000)[:n]
        r = np.zeros(n)
        for i in range(1, n):
            r[i] = sig * rng.standard_normal() + ac * blk[i] * r[i - 1]
    elif name == "season":
        hr = idx.hour.to_numpy() + idx.minute.to_numpy() / 60.0
        r = sig * rng.standard_normal(n) + 0.60 * k * sig * np.sin(2 * np.pi * hr / 24)
    elif name == "volshock":
        # Zero-mean: a shock makes the bar LARGER, and the planted effect is that
        # the move then CONTINUES on the next bar. The earlier version added a
        # one-sided drift to 5% of bars, which is a trend, not a shock, and drove
        # the path to 1e135.
        shock = rng.random(n) < 0.05
        r = sig * rng.standard_normal(n) * np.where(shock, 2.5 * min(k, 3.0), 1.0)
        cont = 0.9 * min(a, 1.0)
        nxt = np.zeros(n)
        nxt[1:] = cont * r[:-1] * shock[:-1]   # continuation after a shock
        r = r + nxt
    elif name == "flow":
        _imb = np.clip(rng.standard_normal(n) * 0.3, -0.9, 0.9)
        r = sig * rng.standard_normal(n)
        lead = np.zeros(n)
        lead[1:] = 2.2 * k * sig * _imb[:-1]     # LEAD: imb[t] drives r[t+1]
        r = r + lead
    else:                                       # null: nothing planted
        r = sig * rng.standard_normal(n)

    close = 30000.0 * np.exp(np.cumsum(r))
    # A synthetic world that is not finite is not a test. The explosive-AR(1) bug
    # above produced inf prices and a silent 0-trade run; this catches it at the
    # source instead of 200 lines downstream as t_stat = nan.
    assert np.isfinite(close).all(), f"world '{name}' produced non-finite prices"
    assert close.min() > 0 and close.max() / close.min() < 1e6, (
        f"world '{name}' price path is degenerate: "
        f"min {close.min():.4g} max {close.max():.4g}")
    sprd = np.abs(rng.standard_normal(n)) * sig * 0.6
    high = close * (1 + sprd)
    low = close * (1 - sprd)
    open_ = np.concatenate([[close[0]], close[:-1]])
    vol = np.abs(rng.standard_normal(n)) * 100 + 50

    if name == "flow":
        # reuse the SAME imbalance that drove the return
        tbb = vol * (_imb + 1.0) / 2.0
    else:
        tbb = vol * rng.uniform(0.35, 0.65, n)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                         "volume": vol, "taker_buy_base": tbb}, index=idx)
