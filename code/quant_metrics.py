#!/usr/bin/env python3
"""
quant_metrics.py — Institutional Quant Trading Metrics & Statistical Validation Library

Provides rigorous financial and statistical tools for systematic strategy research:
  1. Risk-adjusted returns: Annualized Sharpe, Sortino, Calmar, Omega
  2. Autocorrelation & Serial Independence: Ljung-Box test
  3. Stationary Block Bootstrap: Resampling preserving serial dependency
  4. Data Quality & Bar-gap analysis: Detects irregular intervals & stretches
  5. Margin & Liquidation Buffer Analysis: Leveraged perpetual risk verification
  6. Multiple Testing & Overfitting: Deflated Sharpe Ratio (DSR) & PBO (CSCV)
  7. Automated Artifact Scorecard: Computes complete institutional stats on any run
"""
from __future__ import annotations

import math
from statistics import NormalDist
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


# ═════════════════════════════════════════════════════════════════════════════
# 1. RISK-ADJUSTED RETURN METRICS
# ═════════════════════════════════════════════════════════════════════════════

def annualized_sharpe(returns: Union[np.ndarray, pd.Series],
                      periods_per_year: float = 365.25 * 24,
                      rf: float = 0.0) -> float:
    """Annualized Sharpe Ratio from periodic returns."""
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 3:
        return float("nan")
    excess = r - rf / periods_per_year
    sd = np.std(excess, ddof=1)
    if sd <= 1e-14:
        return float("nan")
    return float((np.mean(excess) / sd) * math.sqrt(periods_per_year))


def annualized_sortino(returns: Union[np.ndarray, pd.Series],
                       periods_per_year: float = 365.25 * 24,
                       target_return: float = 0.0) -> float:
    """Annualized Sortino Ratio (downside risk only)."""
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 3:
        return float("nan")
    excess = r - target_return / periods_per_year
    downside = excess[excess < 0]
    if len(downside) < 2:
        return float("inf") if np.mean(excess) > 0 else float("nan")
    downside_dev = math.sqrt(np.mean(downside ** 2))
    if downside_dev <= 1e-14:
        return float("nan")
    return float((np.mean(excess) / downside_dev) * math.sqrt(periods_per_year))


def calmar_ratio(net_return_pct: float,
                 max_dd_pct: float,
                 years: float) -> float:
    """Annualized Calmar Ratio: CAGR / abs(MaxDrawdown)."""
    if years <= 0 or abs(max_dd_pct) <= 1e-6:
        return float("nan")
    cagr_pct = (((1.0 + net_return_pct / 100.0) ** (1.0 / years)) - 1.0) * 100.0
    return float(cagr_pct / abs(max_dd_pct))


def omega_ratio(returns: Union[np.ndarray, pd.Series],
                threshold: float = 0.0) -> float:
    """Omega ratio: probability-weighted ratio of gains vs losses."""
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 2:
        return float("nan")
    diff = r - threshold
    pos = diff[diff > 0]
    neg = diff[diff < 0]
    loss_sum = abs(np.sum(neg))
    if loss_sum <= 1e-14:
        return float("inf") if len(pos) > 0 else float("nan")
    return float(np.sum(pos) / loss_sum)


def historical_var_cvar(returns: Union[np.ndarray, List[float]],
                        levels: Tuple[float, ...] = (0.95, 0.99)) -> Dict[str, float]:
    """
    Historical (non-parametric) Value at Risk and Conditional VaR (Expected
    Shortfall). Convention: LOSS MAGNITUDES are reported POSITIVE in percent
    (daily_var_95_pct = 2.5 means the worst day loses 2.5% or more 5% of the
    time); CVaR is the mean of the observations at least as bad as the VaR
    quantile. Needs a minimum sample to say anything about a tail.
    """
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 10:
        return {}
    out = {"n_obs": int(len(r))}
    for L in levels:
        q = float(np.percentile(r, (1.0 - L) * 100.0))
        tail = r[r <= q]
        if len(tail) == 0:
            tail = np.array([r.min()])
        key = f"{int(round(L * 100))}"
        out[f"var_{key}_pct"] = round(-q * 100.0, 4)
        out[f"cvar_{key}_pct"] = round(-float(tail.mean()) * 100.0, 4)
    return out


# ═════════════════════════════════════════════════════════════════════════════
# 2. AUTOCORRELATION & SERIAL INDEPENDENCE (Ljung-Box)
# ═════════════════════════════════════════════════════════════════════════════

def ljung_box_test(series: Union[np.ndarray, pd.Series],
                   lags: int = 10) -> Dict[str, float]:
    """
    Ljung-Box Q-test for serial autocorrelation.
    H0: The series values are independently distributed (no serial correlation).
    Small p-value (< 0.05) indicates significant autocorrelation (violates i.i.d.).
    """
    x = np.asarray(series, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n <= lags + 2:
        return {"q_stat": float("nan"), "p_val": float("nan"), "lags": lags, "reject_iid": False}

    xm = x - np.mean(x)
    var = np.sum(xm ** 2)
    if var <= 1e-14:
        return {"q_stat": 0.0, "p_val": 1.0, "lags": lags, "reject_iid": False}

    q = 0.0
    for k in range(1, lags + 1):
        rk = np.sum(xm[:-k] * xm[k:]) / var
        q += (rk ** 2) / (n - k)
    q *= n * (n + 2)

    # Chi-square cumulative distribution approximation
    # Using Wilson-Hilferty transformation for chi-sq p-value
    k_df = float(lags)
    if q <= 0:
        p_val = 1.0
    else:
        # Standard normal approx for chi-square CDF
        z = ((q / k_df) ** (1.0 / 3.0) - (1.0 - 2.0 / (9.0 * k_df))) / math.sqrt(2.0 / (9.0 * k_df))
        p_val = 1.0 - NormalDist().cdf(z)
        p_val = max(0.0, min(1.0, float(p_val)))

    return {
        "q_stat": float(round(q, 4)),
        "p_val": float(round(p_val, 4)),
        "lags": lags,
        "reject_iid": bool(p_val < 0.05),
    }


# ═════════════════════════════════════════════════════════════════════════════
# 3. STATIONARY BLOCK BOOTSTRAP (Politis & Romano 1994)
# ═════════════════════════════════════════════════════════════════════════════

def block_bootstrap(data: Union[np.ndarray, List[float]],
                    block_size: Optional[int] = None,
                    draws: int = 20000,
                    seed: int = 7,
                    ci_level: float = 0.95) -> Dict[str, float]:
    """
    Stationary block bootstrap to preserve dependency structure across time.
    Draws geometric blocks with average length = block_size.
    """
    x = np.asarray(data, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 5:
        return {"mean": float("nan"), "ci_lo": float("nan"), "ci_hi": float("nan"),
                "p_le_zero": float("nan"), "t_stat": float("nan"), "block_size": 1}

    if block_size is None or block_size < 1:
        # Optimal default heuristic for stationary block size
        block_size = max(2, int(round(n ** (1.0 / 3.0))))

    p_geom = 1.0 / float(block_size)
    rng = np.random.default_rng(seed)

    boot_means = np.empty(draws)
    for d in range(draws):
        indices = np.empty(n, dtype=int)
        idx = rng.integers(0, n)
        for i in range(n):
            if rng.random() < p_geom:
                idx = rng.integers(0, n)
            else:
                idx = (idx + 1) % n
            indices[i] = idx
        boot_means[d] = np.mean(x[indices])

    alpha = (1.0 - ci_level) / 2.0
    ci_lo = float(np.percentile(boot_means, alpha * 100))
    ci_hi = float(np.percentile(boot_means, (1.0 - alpha) * 100))
    mean_val = float(np.mean(x))
    std_err = float(np.std(boot_means, ddof=1))
    t_stat = mean_val / std_err if std_err > 1e-12 else float("nan")
    p_le_zero = float(np.mean(boot_means <= 0.0))

    return {
        "mean": float(round(mean_val, 4)),
        "ci_lo": float(round(ci_lo, 4)),
        "ci_hi": float(round(ci_hi, 4)),
        "t_stat": float(round(t_stat, 3)),
        "p_le_zero": float(round(p_le_zero, 4)),
        "block_size": int(block_size),
        "draws": draws,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 4. DATA QUALITY & BAR-GAP AUDIT
# ═════════════════════════════════════════════════════════════════════════════

def data_gap_analysis(df: pd.DataFrame,
                      max_allowed_gap_bars: float = 24.0) -> Dict[str, Union[int, float, bool]]:
    """
    Analyzes datetime index intervals for missing bars and data stretches.
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame index must be a DatetimeIndex")
    if len(df) < 2:
        return {"bars": len(df), "missing_bars": 0, "max_gap_bars": 1.0, "gap_breach": False}

    diffs = df.index.to_series().diff().dropna().dt.total_seconds()
    base_sec = float(diffs.median())
    if base_sec <= 0:
        return {"bars": len(df), "missing_bars": 0, "max_gap_bars": 1.0, "gap_breach": False}

    gaps = diffs[diffs > 1.5 * base_sec]
    n_gaps = int(len(gaps))
    missing_bars = int(round(((gaps / base_sec) - 1.0).clip(lower=0).sum())) if n_gaps > 0 else 0
    max_gap_bars = float(round(gaps.max() / base_sec, 1)) if n_gaps > 0 else 1.0

    return {
        "bars": int(len(df)),
        "base_seconds": int(round(base_sec)),
        "n_gaps": n_gaps,
        "missing_bars": missing_bars,
        "max_gap_bars": max_gap_bars,
        "gap_breach": bool(max_gap_bars > max_allowed_gap_bars),
    }


# ═════════════════════════════════════════════════════════════════════════════
# 5. LIQUIDATION & MARGIN BUFFER VERIFICATION
# ═════════════════════════════════════════════════════════════════════════════

def liquidation_risk_check(equity_curve: Union[np.ndarray, List[float]],
                           gross_notional_curve: Union[np.ndarray, List[float]],
                           maint_margin_pct: float = 0.005,
                           leverage_cap: float = 10.0) -> Dict[str, Union[float, int, bool]]:
    """
    Verifies that maintenance margin requirements are never breached throughout
    the equity trajectory under leveraged perpetual contracts.
    """
    eq = np.asarray(equity_curve, dtype=float)
    gross = np.asarray(gross_notional_curve, dtype=float)
    if len(eq) == 0 or len(gross) == 0 or len(eq) != len(gross):
        return {"min_margin_buffer_pct": float("nan"), "liquidation_occurred": False,
                "bars_over_leverage": 0, "max_leverage_reached": 0.0}

    # Maintenance margin required by exchange = gross_notional * maint_margin_pct
    maint_req = gross * maint_margin_pct
    # Margin buffer = (equity - maint_req) / max(equity, 1e-12) * 100
    with np.errstate(divide="ignore", invalid="ignore"):
        buffer_pct = ((eq - maint_req) / np.maximum(eq, 1e-12)) * 100.0
        leverage_realized = gross / np.maximum(eq, 1e-12)

    min_buffer = float(np.nanmin(buffer_pct))
    max_lev = float(np.nanmax(leverage_realized))
    bars_over_lev = int(np.sum(leverage_realized > leverage_cap))
    # Liquidation occurs when equity drops below maintenance margin requirement (buffer <= 0)
    liquidation_occurred = bool(min_buffer <= 0.0)

    return {
        "min_margin_buffer_pct": float(round(min_buffer, 2)),
        "max_leverage_reached": float(round(max_lev, 2)),
        "bars_over_leverage": bars_over_lev,
        "liquidation_occurred": liquidation_occurred,
        "leverage_cap": leverage_cap,
        "maint_margin_pct": maint_margin_pct * 100.0,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 6. OVERFITTING & PROBABILITY OF OVERFITTING (PBO - CSCV)
# ═════════════════════════════════════════════════════════════════════════════

def probabilistic_sharpe(sr: float, n: int, skew: float, kurt: float, sr0: float = 0.0) -> float:
    """Bailey & Lopez de Prado (2012) Probabilistic Sharpe Ratio."""
    if n < 3 or not np.isfinite(sr):
        return float("nan")
    denom = 1.0 - skew * sr + ((kurt - 1.0) / 4.0) * (sr ** 2)
    if denom <= 0:
        return float("nan")
    z = (sr - sr0) * math.sqrt(n - 1.0) / math.sqrt(denom)
    return float(NormalDist().cdf(z))


def deflated_sharpe(returns: Union[np.ndarray, List[float]],
                    trial_sharpes: List[float]) -> Dict[str, float]:
    """Deflated Sharpe Ratio (accounting for multiple testing over N trials)."""
    r = pd.Series(np.asarray(returns, dtype=float)).dropna()
    ts = np.asarray([x for x in trial_sharpes if np.isfinite(x)], dtype=float)
    n = len(r)
    sd = r.std(ddof=1)
    if n < 3 or sd <= 1e-14:
        return {"sr": float("nan"), "sr0": float("nan"), "dsr": float("nan"), "n_trials": int(len(ts))}
    sr = float(r.mean() / sd)
    skew = float(r.skew())
    kurt = float(r.kurt() + 3.0)
    N = len(ts)
    if N >= 2 and ts.var(ddof=1) > 0:
        euler_gamma = 0.5772156649015329
        nd = NormalDist()
        sr0 = math.sqrt(float(ts.var(ddof=1))) * (
            (1.0 - euler_gamma) * nd.inv_cdf(1.0 - 1.0 / N)
            + euler_gamma * nd.inv_cdf(1.0 - 1.0 / (N * math.e))
        )
    else:
        sr0 = 0.0
    dsr = probabilistic_sharpe(sr, n, skew, kurt, sr0)
    return {"sr": round(sr, 4), "sr0": round(sr0, 4), "dsr": round(dsr, 4), "n_trials": int(N)}


def pbo_cscv(perf_matrix: np.ndarray, n_splits: int = 8) -> Dict[str, float]:
    """
    Combinatorially Symmetric Cross-Validation (CSCV) Probability of Backtest Overfitting.
    perf_matrix: T x N array of per-period returns for N candidate parameter sets across T time steps.
    """
    M = np.asarray(perf_matrix, dtype=float)
    if M.ndim != 2 or M.shape[1] < 2:
        raise ValueError("pbo_cscv requires a 2D matrix (T x N) with at least 2 configurations")
    T, N = M.shape
    S = int(n_splits)
    if S % 2 != 0 or S < 4 or T < S * 2:
        raise ValueError("n_splits must be even, >= 4, and T >= 2*n_splits")

    def calc_sr(x):
        sd = x.std(axis=0, ddof=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            s = x.mean(axis=0) / sd
        return np.where(sd > 0, s, -np.inf)

    import itertools
    blocks = np.array_split(np.arange(T), S)
    logits = []
    for comb in itertools.combinations(range(S), S // 2):
        tr_idx = np.concatenate([blocks[b] for b in comb])
        te_idx = np.concatenate([blocks[b] for b in range(S) if b not in comb])
        best_cfg = int(np.argmax(calc_sr(M[tr_idx])))
        s_te = calc_sr(M[te_idx])
        rank = float(np.sum(s_te < s_te[best_cfg]) + 1)
        w = rank / (N + 1.0)
        w = min(max(w, 1e-6), 1.0 - 1e-6)
        logits.append(math.log(w / (1.0 - w)))

    lg = np.asarray(logits)
    pbo = float(np.mean(lg <= 0.0))
    return {
        "pbo": float(round(pbo, 4)),
        "passes_pbo": bool(pbo < 0.50),
        "mean_logit": float(round(np.mean(lg), 4)),
        "n_combos": len(lg),
        "n_configs": N,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 7. ARTIFACT AUDIT SCORECARD GENERATOR
# ═════════════════════════════════════════════════════════════════════════════

def compute_artifact_scorecard(artifact: dict) -> Dict[str, Union[float, int, str, bool, dict]]:
    """
    Computes institutional quant metrics for a loaded artifact dictionary.
    """
    metrics = artifact.get("metrics", {})
    tables = artifact.get("tables") or []
    sym = artifact.get("symbol", "")
    tf = artifact.get("timeframe", "")
    strat = artifact.get("strategy", "")

    # For table-based adapters (cbpack, cbpackf), extract headline strategy row
    headline_strat = None
    if tables and "best_net_id" in metrics:
        bid = metrics.get("best_net_id")
        for r in tables:
            if r.get("id") == bid:
                headline_strat = r
                break

    ret_val = metrics.get("return_pct")
    if ret_val is None:
        ret_val = metrics.get("best_net_pct")
    pf_val = metrics.get("profit_factor")
    if pf_val is None:
        pf_val = metrics.get("best_pf")
    n_trades_val = metrics.get("n_trades")
    if n_trades_val is None and headline_strat:
        n_trades_val = headline_strat.get("trades")
    win_rate_val = metrics.get("win_rate")
    if win_rate_val is None and headline_strat and "win_%" in headline_strat:
        win_rate_val = headline_strat.get("win_%")
    max_dd_val = metrics.get("max_dd_pct")
    if max_dd_val is None and headline_strat and "maxDD_%" in headline_strat:
        max_dd_val = headline_strat.get("maxDD_%")

    # Timeframe to periods per year mapping
    tf_annual = {
        "1m": 365.25 * 24 * 60,
        "5m": 365.25 * 24 * 12,
        "15m": 365.25 * 24 * 4,
        "1h": 365.25 * 24,
        "4h": 365.25 * 6,
        "1d": 365.25,
    }.get(tf, 365.25 * 24)

    # 1. Closed trade statistics & block bootstrap
    trades = artifact.get("trades") or artifact.get("closed_trades") or []
    # If trades are in tables or metrics
    pnl_series = []
    if trades and isinstance(trades, list) and isinstance(trades[0], dict) and "pnl" in trades[0]:
        pnl_series = [float(t["pnl"]) for t in trades if "pnl" in t]
    elif "closed_pnl" in metrics:
        pnl_series = [float(x) for x in metrics.get("closed_pnl", [])]

    boot_res = {}
    autocorr_res = {}
    if pnl_series:
        boot_res = block_bootstrap(pnl_series)
        autocorr_res = ljung_box_test(pnl_series, lags=min(10, max(2, len(pnl_series) // 5)))
    elif "boot_ci_lo" in metrics:
        boot_res = {
            "mean": metrics.get("expectancy_per_trade"),
            "ci_lo": metrics.get("boot_ci_lo"),
            "ci_hi": metrics.get("boot_ci_hi"),
            "t_stat": metrics.get("boot_t"),
            "p_le_zero": metrics.get("boot_p_le_zero"),
            "draws": metrics.get("boot_draws", 20000),
            "block_size": "i.i.d. draws (stored in artifact)",
        }

    # 2. Equity curve analytics
    eqc = artifact.get("equity_curve") or metrics.get("equity_curve") or []
    sharpe_ann = float("nan")
    sortino_ann = float("nan")
    calmar_ann = float("nan")
    var_cvar_res = None

    if eqc and len(eqc) > 2:
        eq_arr = np.asarray(eqc, dtype=float)
        bar_rets = np.diff(eq_arr) / np.maximum(eq_arr[:-1], 1e-12)
        sharpe_ann = annualized_sharpe(bar_rets, periods_per_year=tf_annual)
        sortino_ann = annualized_sortino(bar_rets, periods_per_year=tf_annual)
        bars_count = len(eq_arr)
        years = bars_count / tf_annual
        ret_pct = float(metrics.get("return_pct", 0.0))
        max_dd = abs(float(metrics.get("max_dd_pct", 1.0)))
        calmar_ann = calmar_ratio(ret_pct, max_dd, years)

        # Tail risk: daily-resampled returns (compound within each day) plus
        # the raw per-bar series. Daily needs at least one full day of bars.
        bpd = max(1, int(round(tf_annual / 365.25)))
        n_full = (len(bar_rets) // bpd) * bpd
        vc = {}
        if n_full >= bpd:
            daily = np.prod(1.0 + bar_rets[:n_full].reshape(-1, bpd), axis=1) - 1.0
            vc = historical_var_cvar(daily, levels=(0.95, 0.99))
            if vc:
                vc["n_days"] = int(n_full // bpd)
                vc["bars_per_day"] = int(bpd)
        bar_vc = historical_var_cvar(bar_rets, levels=(0.95, 0.99))
        if bar_vc:
            vc["bar_n_obs"] = bar_vc["n_obs"]
            for k in ("var_95_pct", "cvar_95_pct", "var_99_pct", "cvar_99_pct"):
                vc[f"bar_{k}"] = bar_vc.get(k)
        var_cvar_res = vc if vc else None

    if not np.isfinite(calmar_ann):
        inputs = artifact.get("inputs", [])
        if inputs and isinstance(inputs[0], dict) and "start" in inputs[0] and "end" in inputs[0]:
            try:
                t0 = pd.to_datetime(inputs[0]["start"], utc=True)
                t1 = pd.to_datetime(inputs[0]["end"], utc=True)
                years = max(0.1, (t1 - t0).total_seconds() / (365.25 * 86400))
                if ret_val is not None and max_dd_val is not None:
                    calmar_ann = calmar_ratio(float(ret_val), abs(float(max_dd_val)), years)
            except Exception:
                pass

    if not np.isfinite(sharpe_ann):
        if "sharpe" in metrics:
            sharpe_ann = float(metrics["sharpe"])
        elif headline_strat and "sharpe" in headline_strat:
            sharpe_ann = float(headline_strat["sharpe"])

    if not np.isfinite(sortino_ann):
        if "sortino" in metrics:
            sortino_ann = float(metrics["sortino"])
        elif headline_strat and "sortino" in headline_strat:
            sortino_ann = float(headline_strat["sortino"])

    if not np.isfinite(calmar_ann):
        if "calmar" in metrics:
            calmar_ann = float(metrics["calmar"])
        elif headline_strat and "calmar" in headline_strat:
            calmar_ann = float(headline_strat["calmar"])

    # 3. Liquidation buffer
    liq_res = {}
    if "min_margin_buffer_pct" in metrics:
        liq_res = {
            "min_margin_buffer_pct": metrics.get("min_margin_buffer_pct"),
            "max_leverage_reached": metrics.get("max_gross_leverage"),
            "bars_over_leverage": metrics.get("bars_over_leverage", 0),
            "liquidation_occurred": bool(float(metrics.get("min_margin_buffer_pct", 100)) <= 0),
        }

    conc_info = None
    if headline_strat and "conc_passes" in headline_strat:
        conc_info = {
            "top5_share_pct": headline_strat.get("conc_top5_share_pct"),
            "conc_passes": bool(headline_strat.get("conc_passes")),
            "net_without_top5_pct": headline_strat.get("conc_net_without_top5_pct"),
        }

    return {
        "run_id": artifact.get("run_id"),
        "strategy": strat,
        "symbol": sym,
        "timeframe": tf,
        "headline_strat": headline_strat.get("id") if headline_strat else None,
        "return_pct": ret_val,
        "profit_factor": pf_val,
        "n_trades": n_trades_val,
        "win_rate": win_rate_val,
        "max_dd_pct": max_dd_val,
        "sharpe_annualized": round(sharpe_ann, 3) if np.isfinite(sharpe_ann) else None,
        "sortino_annualized": round(sortino_ann, 3) if np.isfinite(sortino_ann) else None,
        "calmar_ratio": round(calmar_ann, 3) if np.isfinite(calmar_ann) else None,
        "concentration": conc_info,
        "var_cvar": var_cvar_res,
        "block_bootstrap": boot_res,
        "autocorrelation_ljung_box": autocorr_res,
        "liquidation_check": liq_res,
    }
