"""build_features -- the base frame every strategy joins onto.

Returns exactly what strategies.py needs: columns `sig`, `fwd_ret`, `y`.
    sig      per-bar volatility (causal), the normaliser every strategy divides by
    fwd_ret  forward log return over cfg.horizon_bars  -- THE LABEL SOURCE
    y        1.0 if fwd_ret > 0 else 0.0, NaN on the last h bars

CAUSALITY
    `sig` uses a trailing window only. `fwd_ret` looks forward by construction
    because it is the label, and it is never a feature: strategies.py receives
    only `sig` plus OHLCV, and `strategy_frame` joins `fwd_ret`/`y` back in as
    labels only. The walk-forward embargo (model.py) is h+1 bars so no training
    label overlaps a test bar.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def build_features(df: pd.DataFrame, cfg) -> pd.DataFrame:
    c = df["close"].astype(float)
    lr = np.log(c).diff()
    sig = lr.rolling(cfg.vol_window).std()
    # a floor, so dividing by sig cannot explode on a flat stretch
    med = sig.rolling(288, min_periods=48).median()
    sig = sig.where(sig > 0, np.nan).clip(lower=1e-7)
    _ = med  # kept for readability of intent; floor is the clip above

    h = cfg.horizon_bars
    fwd = np.log(c.shift(-h) / c)
    out = pd.DataFrame(index=df.index)
    out["sig"] = sig
    out["fwd_ret"] = fwd
    y = (fwd > 0).astype(float)
    y[fwd.isna()] = np.nan
    out["y"] = y

    # `sig` is the denominator of every strategy's features. If it is empty the
    # whole suite returns 0 trades and t_stat = nan, which reads as "no edge"
    # rather than "broken input". Assert it here, once.
    n_sig = int(sig.notna().sum())
    assert n_sig > 0.5 * len(df), (
        f"build_features produced sig on only {n_sig}/{len(df)} bars -- the "
        f"price series is probably degenerate (check finite, positive close)")
    return out
