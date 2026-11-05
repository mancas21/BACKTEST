"""run_backtest / permutation_control -- costs, decision, and the null control.

CONTRACT (from suite.py)
    net   = run_backtest(df, cfg,  p=p, feats=feats)
    gross = run_backtest(df, gross_cfg, p=p, feats=feats)     # costs zeroed
    net.metrics["calibration"] -> auc/slope
    permutation_control(df, net, cfg, n=, seed=) -> {"percentile": ...}

DECISION RULE (the pack's own formula, from its SKILL.md)
    "|2p-1| * E|ret| debe superar el costo ida y vuelta"
    expected move  E|ret| = sig * sqrt(h) * sqrt(2/pi)      (causal: sig is trailing)
    expected edge         = |2p-1| * E|ret|
    round-trip cost       = 2*(fee_taker + slippage) + funding over the hold
    trade when            edge > cost + min_edge
    side                  long if p > 0.5 else short

    E|ret| is derived from the TRAILING volatility and the horizon only. Using
    the realised forward return's magnitude would be look-ahead and would make
    the gate self-fulfilling.

WHY GROSS IS A SEPARATE RUN, NOT A RE-PRICE OF NET
    suite.py calls run_backtest with the SAME p under a config whose costs are 0.
    The gate therefore differs between the two runs, which is the point: `gross t`
    answers "is there any alpha before fees at all", and a high gross t beside a
    failing net t is exactly the signature of an edge that costs eat. Calling it
    "the same signals at zero cost" is their description and it is faithful.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

from .model import calibration


@dataclass
class BacktestResult:
    metrics: dict
    trades: pd.DataFrame
    # carried so permutation_control(df, net, cfg) can re-run the SAME pipeline
    # under a shuffled prediction -- its call signature in suite.py has no other
    # way to reach the features.
    feats: object = None
    p: object = None


def _cost_per_trade(cfg) -> float:
    """Round-trip cost as a RETURN fraction, including funding over the hold."""
    fees = 2.0 * (cfg.fee_taker + cfg.slippage)
    hold_min = cfg.horizon_bars * cfg.interval_min
    funding = cfg.funding_8h * (hold_min / 480.0)
    return fees + funding


def run_backtest(df: pd.DataFrame, cfg, p: pd.Series, feats: pd.DataFrame) -> BacktestResult:
    h = cfg.horizon_bars
    sig = feats["sig"].to_numpy(float)
    fwd = feats["fwd_ret"].to_numpy(float)
    y = feats["y"].to_numpy(float)
    pv = p.to_numpy(float) if isinstance(p, pd.Series) else np.asarray(p, float)

    with np.errstate(invalid="ignore"):
        e_abs = sig * np.sqrt(h) * np.sqrt(2.0 / np.pi)      # E|ret|, causal
        edge = np.abs(2.0 * pv - 1.0) * e_abs
    cost = _cost_per_trade(cfg)
    take = np.isfinite(edge) & np.isfinite(fwd) & (edge > cost + cfg.min_edge)
    side = np.where(pv > 0.5, 1.0, -1.0)

    gross_ret = np.where(take, side * fwd, np.nan)
    net_ret = np.where(take, side * fwd - cost, np.nan)

    n = int(take.sum())
    metrics = {
        "n_trades": n,
        "n_bars": len(feats),
        "min_edge_bp": cfg.min_edge * 1e4,
        "cost_bp": cost * 1e4,
        "t_stat": float("nan"),
        "net_return": 0.0,
        "gross_edge_bp": float(np.nanmean(edge[take]) * 1e4) if n else 0.0,
        "avg_net_bp": float(np.nanmean(net_ret) * 1e4) if n else 0.0,
        "avg_gross_bp": float(np.nanmean(gross_ret) * 1e4) if n else 0.0,
        "max_dd": 0.0,
        "bh_return": float(df["close"].iloc[-1] / df["close"].iloc[0] - 1.0),
        "calibration": calibration(y, pv),
    }
    if n >= 2:
        r = net_ret[take]
        r = r[np.isfinite(r)]
        if len(r) >= 2 and r.std(ddof=1) > 0:
            metrics["t_stat"] = float(r.mean() / (r.std(ddof=1) / np.sqrt(len(r))))
        # compound the per-trade returns, all trades equally sized off equity
        eq = np.cumprod(1.0 + r) if len(r) else np.array([1.0])
        metrics["net_return"] = float(eq[-1] - 1.0)
        peak = np.maximum.accumulate(eq)
        metrics["max_dd"] = float(np.max((peak - eq) / peak)) if len(eq) else 0.0

    trades = pd.DataFrame({"p": pv[take], "side": side[take], "fwd": fwd[take],
                           "gross": gross_ret[take], "net": net_ret[take]},
                          index=feats.index[take])
    return BacktestResult(metrics=metrics, trades=trades, feats=feats, p=p)


def permutation_control(df: pd.DataFrame, net: "BacktestResult", cfg, n: int = 5, seed: int = 0) -> dict:
    """Null by shuffling the prediction series, re-running the whole backtest.

    Shuffling p destroys any link between prediction and outcome while keeping
    p's marginal distribution and the trade-rate mechanism intact, so the
    permuted t-stats form a proper null for "this signal carries nothing".
    Shuffling the LABELS instead would force a refit per draw and is
    prohibitively slow for the same answer.

    percentile = share of permuted t-stats the real t beats. suite.py requires
    >= 0.90 -- i.e. the real signal must beat 90% of its own scrambled versions.
    """
    real = net.metrics["t_stat"]
    if not np.isfinite(real) or net.feats is None or net.p is None:
        return {"percentile": float("nan"), "perm_t": []}
    rng = np.random.default_rng(seed)
    pv = net.p.to_numpy(float)
    ts = []
    for _ in range(n):
        sh = rng.permutation(pv)
        r = run_backtest(df, cfg, p=pd.Series(sh, index=net.p.index), feats=net.feats)
        ts.append(r.metrics["t_stat"])
    ts = np.array(ts, float)
    valid = np.isfinite(ts)
    pct = float((ts[valid] < real).mean()) if valid.any() else float("nan")
    return {"percentile": pct, "perm_t": ts.tolist()}
