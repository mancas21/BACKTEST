# edge_stats.py -- VENDORED copy of edge/engine/stats.py (do not edit here).
#
# Source        : edge/engine/stats.py
# Source sha256 : 91012638d3d447f355380c8e44e3b1e69831defda56cd1b665edd1abe2837457
# Origin        : EDGE-first research project v4.1 / v6 bridge (MP section 8),
#                 migrated into this repository 2026-10-29.
# Why vendored  : `code/` is where the harness lives. Importing across the two
#                 trees would couple the backtest harness to a sealed, terminal
#                 research campaign. The copy carries this provenance header;
#                 everything below the marker line is BYTE-IDENTICAL.
# Parity        : `python code/_edge_stats_vendor.py --check` compares the body
#                 below the marker against edge/engine/stats.py.
#
# NEW to this repository (grep over code/ before the import: zero files
# contained any of them):
#   cluster_t              day-clustered CR1 t-statistic of per-trade net bps
#   benjamini_hochberg     FDR (BH) across ALL ledger screens -- the gate that
#                          pack50 and cand7 could not apply to their own trials
#   spa_test               Hansen (2005) SPA / reality check
#   mde_bps, effective_n   minimum detectable effect and the power statement
#   matched_timing_null    matched-hour timing null
#   circular_shift_null    circular-shift null for event studies
#   factor_regression      Newey-West factor regression vs BTC + basket
#
# NOT new -- already in code/quant_metrics.py; this file is not their canonical
# source, they are kept only for API parity with the original engine:
#   deflated_sharpe, pbo_cscv, sharpe_ratio, stationary_bootstrap_idx
#
# Requires numpy + scipy (both present in the repo environment).
# --- BEGIN edge/engine/stats.py (byte-identical) ---
"""Statistics (MP §8). Everything seeded; no hidden randomness.

- cluster_t: day-clustered t-statistic of per-trade net bps
- benjamini_hochberg: FDR across ALL ledger screens
- stationary_bootstrap: Politis-Romano day-block bootstrap CIs
- matched_timing_null / circular_shift_null (§8.3)
- mde_bps (§8.2 power statement)
- deflated_sharpe (Bailey & Lopez de Prado), spa_test (Hansen 2005), pbo_cscv (§8.4)
- factor_regression NW (§8.1)
"""
import math

import numpy as np
from scipy import stats as sps


def cluster_t(x: np.ndarray, day_ids: np.ndarray) -> float:
    """t-stat of mean(x) with clusters = unique days (Liang-Zeger CR1)."""
    x = np.asarray(x, float)
    if len(x) < 2:
        return 0.0
    mean = x.mean()
    uniq, inv = np.unique(day_ids, return_inverse=True)
    G = len(uniq)
    if G < 2:
        return 0.0
    sums = np.bincount(inv, weights=x, minlength=G)
    cnts = np.bincount(inv, minlength=G)
    cm = sums / cnts
    # cluster-robust variance of mean = sum_g (n_g * (cm_g - mean))^2 / N^2, with G/(G-1) correction
    var = np.sum(cnts ** 2 * (cm - mean) ** 2) / (len(x) ** 2) * (G / (G - 1))
    if var <= 0:
        return 0.0
    return float(mean / math.sqrt(var))


def t_to_p_two_sided(t: float, dof: float = None) -> float:
    if dof is None or dof <= 0:
        dof = 1e6
    return float(2 * sps.t.sf(abs(t), df=dof))


def benjamini_hochberg(pvals, q: float = 0.10):
    """Return boolean array: rejected (significant) at level q."""
    p = np.asarray(pvals, float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order] * n / (np.arange(1, n + 1))
    thresh = np.minimum.accumulate(ranked[::-1])[::-1]
    rej_sorted = ranked <= q
    out = np.zeros(n, bool)
    out[order] = rej_sorted
    return out, thresh


def stationary_bootstrap_idx(n: int, avg_block: float, reps: int, rng) -> np.ndarray:
    """Politis-Romano stationary bootstrap indices, shape (reps, n)."""
    p = 1.0 / max(avg_block, 1.0)
    out = np.empty((reps, n), dtype=np.int64)
    starts = rng.integers(0, n, size=reps)
    out[:, 0] = starts
    for j in range(1, n):
        redraw = rng.random(reps) < p
        starts[redraw] = rng.integers(0, n, size=redraw.sum())
        out[:, j] = starts
        starts = (starts + 1) % n
    return out


def bootstrap_ci(x: np.ndarray, day_ids: np.ndarray, reps: int = 5000, seed: int = 42,
                 avg_block_days: float = 3.0):
    """CI for the mean of day-level observations via stationary bootstrap on days."""
    uniq, inv = np.unique(day_ids, return_inverse=True)
    day_means = np.bincount(inv, weights=x, minlength=len(uniq)) / np.bincount(inv, minlength=len(uniq))
    rng = np.random.default_rng(seed)
    idx = stationary_bootstrap_idx(len(uniq), avg_block_days, reps, rng)
    boots = day_means[idx].mean(axis=1)
    return float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def matched_timing_null(event_times_ms, event_day_ids, event_ret, event_sym, event_side,
                        pool_times_ms, pool_day_ids, pool_ret, pool_sym, pool_side,
                        pool_hour_bucket, pool_vol_bucket, ev_hour_bucket, ev_vol_bucket,
                        reps: int = 1000, seed: int = 42):
    """Null: same count, side mix, holding-time dist, per-symbol allocation, drawn from
    the same hour-of-week x vol-tercile buckets (§8.3). Returns p-value of observed mean.
    All arrays aligned by event; pools are candidate events (net bps) with bucket labels."""
    rng = np.random.default_rng(seed)
    obs = float(np.mean(event_ret))
    n_ev = len(event_ret)
    # bucket key per event
    keys = np.array([f"{h}|{v}|{s}|{d}" for h, v, s, d in
                     zip(ev_hour_bucket, ev_vol_bucket, event_sym, event_side)])
    pool_keys = np.array([f"{h}|{v}|{s}|{d}" for h, v, s, d in
                          zip(pool_hour_bucket, pool_vol_bucket, pool_sym, pool_side)])
    by_key = {}
    for k in np.unique(pool_keys):
        by_key[k] = np.where(pool_keys == k)[0]
    # holding-time distribution: resample holding-time ranks via random permutation within pool
    null_means = np.empty(reps)
    ev_counts = {k: int((keys == k).sum()) for k in np.unique(keys)}
    for b in range(reps):
        picks = []
        for k, cnt in ev_counts.items():
            cand = by_key.get(k)
            if cand is None or len(cand) == 0:
                # fall back to same hour bucket only
                cand = by_key.get(k.split("|")[0] + "|", None)
                if cand is None:
                    continue
            picks.append(rng.choice(cand, size=cnt, replace=True))
        if not picks:
            null_means[b] = np.nan
            continue
        sel = np.concatenate(picks)
        # preserve side mix exactly: shuffle signs to match observed side proportions
        null_means[b] = pool_ret[sel].mean()
    null_means = null_means[~np.isnan(null_means)]
    p = float((np.sum(null_means >= obs) + 1) / (len(null_means) + 1))
    return p, obs, null_means


def circular_shift_null(signal: np.ndarray, fwd_ret: np.ndarray, event_rule, obs_stat: float,
                        reps: int = 1000, seed: int = 42):
    """Circular signal shift (§8.3): shift the signal series by random offsets (preserves
    autocorrelation), recompute the event statistic via event_rule(shifted_signal, fwd_ret).
    event_rule returns a scalar statistic."""
    rng = np.random.default_rng(seed)
    n = len(signal)
    stats_ = np.empty(reps)
    for b in range(reps):
        k = int(rng.integers(1, n))
        stats_[b] = event_rule(np.roll(signal, k), fwd_ret)
    p = float((np.sum(stats_ >= obs_stat) + 1) / (reps + 1))
    return p, stats_


def mde_bps(sigma_trade_bps: float, n_eff: float, power: float = 0.80,
            alpha: float = 0.05) -> float:
    """Minimum detectable net edge per trade (§8.2): 2.8 * sigma / sqrt(N_eff)."""
    if n_eff <= 0:
        return float("inf")
    z_a = sps.norm.ppf(1 - alpha / 2)
    z_p = sps.norm.ppf(power)
    return float((z_a + z_p) * sigma_trade_bps / math.sqrt(n_eff))


def effective_n(day_ids: np.ndarray) -> float:
    """N_eff under day-clustering: (sum 1)^2 / sum(cluster_size^2)."""
    _, cnts = np.unique(day_ids, return_counts=True)
    return float(len(day_ids) ** 2 / np.sum(cnts ** 2))


# ---------------- multiple testing on daily return streams ----------------

def sharpe_ratio(daily: np.ndarray, rf: float = 0.0, periods: int = 365) -> float:
    d = np.asarray(daily, float) - rf / periods
    if len(d) < 2 or d.std(ddof=1) == 0:
        return 0.0
    return float(d.mean() / d.std(ddof=1) * math.sqrt(periods))


def deflated_sharpe(daily: np.ndarray, sr_trials: np.ndarray = None,
                    periods: int = 365) -> float:
    """DSR = P(SR* <= SR_hat) with SR0 from cross-trial SR variance (§8.4).
    If sr_trials is None, uses SR0=0 (i.e., PSR)."""
    r = np.asarray(daily, float)
    T = len(r)
    if T < 20:
        return 0.0
    sr_hat = r.mean() / r.std(ddof=1) if r.std(ddof=1) > 0 else 0.0  # per-period SR
    skew = float(sps.skew(r))
    kurt = float(sps.kurtosis(r, fisher=False))
    denom = math.sqrt(max(1e-18, 1 - skew * sr_hat + (kurt - 1) / 4 * sr_hat ** 2))
    if sr_trials is not None and len(sr_trials) > 1:
        srs = np.asarray(sr_trials, float) / math.sqrt(periods)  # annual -> per-period
        var_sr = srs.var(ddof=1)
        N = len(srs)
        gamma = 0.5772156649
        emax_var = var_sr * ((1 - gamma) * sps.norm.ppf(1 - 1.0 / N) +
                             gamma * sps.norm.ppf(1 - 1.0 / (N * math.e)))
        sr0 = math.sqrt(max(var_sr, 0)) * ((1 - gamma) * sps.norm.ppf(1 - 1.0 / N) +
                                           gamma * sps.norm.ppf(1 - 1.0 / (N * math.e)))
        sr0 = float(sr0)
    else:
        sr0 = 0.0
    z = (sr_hat - sr0) * math.sqrt(T - 1) / denom
    return float(sps.norm.cdf(z))


def spa_test(trial_daily: np.ndarray, bench_daily: np.ndarray, reps: int = 10000,
             seed: int = 42, avg_block_days: float = 3.0) -> float:
    """Hansen (2005) consistent SPA p-value vs a benchmark (§8.4).
    trial_daily: (T, N) matrix of trial excess daily returns over benchmark.
    Returns p = P(max_j T^0.5 (mean_j - recentered) >= observed max) under bootstrap."""
    T, N = trial_daily.shape
    rng = np.random.default_rng(seed)
    mu = trial_daily.mean(axis=0)
    sd = trial_daily.std(axis=0, ddof=1)
    sd[sd == 0] = np.nan
    # standardized statistic (Hansen SPA-t): avoids useless-trial domination
    t_obs = np.sqrt(T) * mu / sd
    t_obs_max = np.nanmax(t_obs)
    idx = stationary_bootstrap_idx(T, avg_block_days, reps, rng)
    exceed = 0
    for b in range(reps):
        sample = trial_daily[idx[b]]           # (T, N)
        mu_b = sample.mean(axis=0)
        sd_b = sample.std(axis=0, ddof=1)
        sd_b[sd_b == 0] = np.nan
        # recenter by own mean under H0 (conservative SPA-c)
        t_b = np.sqrt(T) * (mu_b - mu) / sd_b
        if np.nanmax(t_b) >= t_obs_max:
            exceed += 1
    return float((exceed + 1) / (reps + 1))


def pbo_cscv(returns_matrix: np.ndarray, S: int = 16, seed: int = 42,
             max_combos: int = 12870) -> float:
    """Probability of Backtest Overfitting via CSCV (§8.4). returns_matrix: (T, N configs)
    of daily returns. Splits T into S blocks; for every C(S, S/2) train/test combination,
    ranks configs in-sample by mean, computes out-of-sample relative rank lambda of the
    in-sample best half. PBO = P(lambda <= 0)."""
    T, N = returns_matrix.shape
    if T < S or N < 2:
        return float("nan")
    blocks = np.array_split(np.arange(T), S)
    from itertools import combinations
    combos = list(combinations(range(S), S // 2))
    if len(combos) > max_combos:
        rng = np.random.default_rng(seed)
        sel = rng.choice(len(combos), max_combos, replace=False)
        combos = [combos[i] for i in sel]
    lam = []
    for tr_blocks in combos:
        te_blocks = [b for b in range(S) if b not in tr_blocks]
        tr_idx = np.concatenate([blocks[b] for b in tr_blocks])
        te_idx = np.concatenate([blocks[b] for b in te_blocks])
        is_mu = returns_matrix[tr_idx].mean(axis=0)
        rank_is = np.argsort(np.argsort(-is_mu))          # 0 = best
        best = rank_is < N // 2                            # in-sample top half
        oos_mu = returns_matrix[te_idx].mean(axis=0)
        rank_oos = np.argsort(np.argsort(-oos_mu))
        rel = 1.0 - (rank_oos[best] / (N - 1))            # 1 = best OOS, 0 = worst
        omega = float(rel.mean())
        lam.append(math.log(max(omega, 1e-9) / max(1 - omega, 1e-9)))
    lam = np.asarray(lam)
    return float((lam <= 0).mean())


def factor_regression(daily: np.ndarray, btc: np.ndarray, basket: np.ndarray,
                      nw_lags: int = 5) -> dict:
    """Daily returns on [1, BTC, EW-alt-basket], Newey-West SEs (§8.1)."""
    y = np.asarray(daily, float)
    X = np.column_stack([np.ones(len(y)), np.asarray(btc, float), np.asarray(basket, float)])
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    T = len(y)
    S = e[:, None] * X
    V = S.T @ S
    for l in range(1, nw_lags + 1):
        w = 1 - l / (nw_lags + 1)
        G = S[l:].T @ S[:-l]
        V += w * (G + G.T)
    V = V / T
    cov = XtX_inv @ V @ XtX_inv
    se = np.sqrt(np.maximum(np.diag(cov), 0))
    resid_ss = float(e @ e)
    total_ss = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - resid_ss / total_ss if total_ss > 0 else 0.0
    return {"alpha_daily": float(beta[0]), "alpha_ann": float(beta[0] * 365),
            "beta_btc": float(beta[1]), "beta_basket": float(beta[2]),
            "t_alpha": float(beta[0] / se[0]) if se[0] > 0 else 0.0,
            "t_btc": float(beta[1] / se[1]) if se[1] > 0 else 0.0,
            "t_basket": float(beta[2] / se[2]) if se[2] > 0 else 0.0,
            "r2": r2, "nw_lags": nw_lags}


def t_to_p_one_sided_gt(t: float, dof: float = None) -> float:
    """One-sided p for H1: mean > 0 (used for BH on the edge hypothesis)."""
    if dof is None or dof <= 0:
        dof = 1e6
    return float(sps.t.sf(t, df=dof))
