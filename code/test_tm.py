"""
Run:  python -m pytest -q test_tm.py     (or)   python test_tm.py
Tests: primitives vs naive references, causality, ratchet invariants, legacy-bug reproduction,
legacy/fixed parity, backtest accounting identities, DSR formula, null/power experiments.
"""
from __future__ import annotations

import math
import sys

import numpy as np
import pandas as pd

from tm_backtest import (BTConfig, deflated_sharpe, expected_max_sharpe, periods_per_year, perf, run_backtest,
                         sweep, target_position, walk_forward)
from tm_core import (MA_TYPES, TMParams, cci, ema, rma, sma, true_range, trend_magic, vwma, wma)
from tm_data import synth_ohlcv


# ----------------------------------------------------------------------------- helpers
def df_from_close(c, rng, wick=0.002) -> pd.DataFrame:
    c = np.asarray(c, float)
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + wick * rng.random(len(c)))
    l = np.minimum(o, c) * (1 - wick * rng.random(len(c)))
    idx = pd.date_range("2024-01-01", periods=len(c), freq="1h", tz="UTC")
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": rng.uniform(1, 2, len(c))}, index=idx)


def close_eq(a, b, tol=1e-9):
    a, b = np.asarray(a, float), np.asarray(b, float)
    assert a.shape == b.shape
    assert np.array_equal(np.isnan(a), np.isnan(b)), "NaN pattern differs"
    m = ~np.isnan(a)
    assert np.allclose(a[m], b[m], rtol=tol, atol=tol), np.max(np.abs(a[m] - b[m]))


# ----------------------------------------------------------------------------- naive references
def ref_sma(x, n):
    return np.array([np.nan] * (n - 1) + [np.mean(x[i - n + 1:i + 1]) for i in range(n - 1, len(x))])


def ref_ema(x, n):
    a, s, out = 2 / (n + 1), x[0], [x[0]]
    for v in x[1:]:
        s = a * v + (1 - a) * s
        out.append(s)
    return np.array(out)


def ref_rma(x, n):
    s = np.mean(x[:n])
    out = [np.nan] * (n - 1) + [s]
    for v in x[n:]:
        s = (v + (n - 1) * s) / n
        out.append(s)
    return np.array(out)


def ref_wma(x, n):
    w = np.arange(1, n + 1)
    return np.array([np.nan] * (n - 1) + [np.dot(x[i - n + 1:i + 1], w) / w.sum() for i in range(n - 1, len(x))])


def ref_cci(x, n):
    out = [np.nan] * (n - 1)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        m = w.mean()
        dev = np.mean(np.abs(w - m))
        out.append((x[i] - m) / (0.015 * dev))
    return np.array(out)


def ref_tr(h, l, c):
    out = [h[0] - l[0]]
    for i in range(1, len(c)):
        out.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    return np.array(out)


# ----------------------------------------------------------------------------- primitives
def test_primitives_match_references():
    rng = np.random.default_rng(1)
    df = synth_ohlcv(500, seed=3)
    x = df["close"].to_numpy()
    v = df["volume"].to_numpy()
    for n in (3, 14, 50):
        close_eq(sma(x, n), ref_sma(x, n), 1e-9)
        close_eq(ema(x, n), ref_ema(x, n))
        close_eq(rma(x, n), ref_rma(x, n))
        close_eq(wma(x, n), ref_wma(x, n))
        close_eq(vwma(x, v, n), ref_sma(x * v, n) / ref_sma(v, n))
        close_eq(cci(x, n), ref_cci(x, n), 1e-8)
    close_eq(true_range(df["high"], df["low"], df["close"]), ref_tr(df["high"].to_numpy(), df["low"].to_numpy(), x))
    assert rng is not None


def test_cci_na_on_flat_window():
    x = np.r_[np.full(30, 5.0), np.arange(30, dtype=float) + 5]
    out = cci(x, 20)
    assert np.isnan(out[19:30]).all() and np.isfinite(out[49:]).all()


# ----------------------------------------------------------------------------- causality
def _cases():
    yield "fixed", TMParams()
    yield "fixed", TMParams(flip_on="close", atr_type="RMA(TR)")
    for m in MA_TYPES:
        yield "fixed", TMParams(smooth=True, ma_type=m, ma_len=9)
    yield "legacy", TMParams()


def test_causality_truncation_and_future_perturbation():
    df = synth_ohlcv(700, seed=11)
    rng = np.random.default_rng(5)
    for mode, p in _cases():
        full = trend_magic(df, p, mode)
        for k in (120, 333, 600):
            part = trend_magic(df.iloc[:k + 1], p, mode)
            for col in ("atr", "cci", "raw", "line", "dir", "sig", "dist_atr"):
                close_eq(full[col].to_numpy()[:k + 1], part[col].to_numpy())
            d2 = df.copy()
            for col in ("open", "high", "low", "close", "volume"):
                d2.iloc[k + 1:, d2.columns.get_loc(col)] *= rng.uniform(0.5, 2, len(d2) - k - 1)
            pert = trend_magic(d2, p, mode)
            for col in ("raw", "line", "dir", "sig"):
                close_eq(full[col].to_numpy()[:k + 1], pert[col].to_numpy()[:k + 1])


# ----------------------------------------------------------------------------- fixed-engine invariants
def test_fixed_has_no_nan_after_warmup_and_never_zero():
    df = synth_ohlcv(2000, seed=2)
    p = TMParams()
    tm = trend_magic(df, p)
    first = max(p.cci_len, p.atr_len) - 1
    assert tm["line"].iloc[:first].isna().all()
    assert tm["line"].iloc[first:].notna().all()
    assert (tm["line"].iloc[first:] > 0).all()
    assert (tm["dir"].iloc[first:] != 0).all()


def test_ratchet_is_monotone_within_regime():
    df = synth_ohlcv(5000, seed=4)
    tm = trend_magic(df, TMParams()).dropna(subset=["raw"])
    d = tm["raw"].diff().to_numpy()[1:]
    up = tm["up"].to_numpy()[1:]
    assert (d[up] >= -1e-12).all() and (d[~up] <= 1e-12).all()


def test_smoothing_never_changes_ratchet_state():
    df = synth_ohlcv(3000, seed=6)
    base = trend_magic(df, TMParams())
    for m in MA_TYPES:
        sm = trend_magic(df, TMParams(smooth=True, ma_type=m, ma_len=14))
        close_eq(base["raw"].to_numpy(), sm["raw"].to_numpy())
        assert not np.allclose(base["line"].to_numpy()[100:], sm["line"].to_numpy()[100:], equal_nan=True)


# ----------------------------------------------------------------------------- legacy bug reproduction + parity
def test_legacy_zero_seed_bug_is_real_and_fixed_engine_avoids_it():
    rng = np.random.default_rng(0)
    c = 100 - 0.5 * np.arange(80) + rng.normal(0, 0.02, 80)           # CCI < 0 from its first valid bar
    df = df_from_close(c, rng)
    leg, fix = trend_magic(df, mode="legacy"), trend_magic(df, mode="fixed")
    assert leg["cci"].iloc[19] < 0
    assert (leg["raw"].iloc[4:] == 0.0).all()                          # line stuck at 0
    assert (leg["dir"] == 0).all() and (leg["sig"] == 0).all()         # never produces a direction
    assert (fix["line"].iloc[19:] > 0).all() and (fix["dir"].iloc[19:] == -1).all()


def test_legacy_na_cci_runs_bearish_branch_during_warmup():
    df = synth_ohlcv(60, seed=1)
    leg = trend_magic(df, mode="legacy")
    assert leg["raw"].iloc[:4].isna().all()
    assert not leg["up"].iloc[:19].any()                               # na CCI treated as bearish


def test_legacy_and_fixed_agree_after_first_legacy_signal_when_cci_starts_positive():
    rng = np.random.default_rng(3)
    tail = synth_ohlcv(1500, seed=8)["close"].to_numpy()
    c = np.r_[100 + 0.5 * np.arange(40), tail / tail[0] * 119.5]
    df = df_from_close(c, rng)
    leg, fix = trend_magic(df, mode="legacy"), trend_magic(df, mode="fixed")
    assert leg["cci"].iloc[19] >= 0
    first = max(19, 4)
    close_eq(leg["raw"].to_numpy()[first:], fix["raw"].to_numpy()[first:])
    k = int(np.flatnonzero(leg["sig"].to_numpy() != 0)[0])
    assert (leg["dir"].to_numpy()[k:] == fix["dir"].to_numpy()[k:]).all()
    assert (leg["sig"].to_numpy()[k + 1:] == fix["sig"].to_numpy()[k + 1:]).all()


# ----------------------------------------------------------------------------- backtest accounting
def test_flat_book_has_flat_equity():
    df = synth_ohlcv(300, seed=1)
    res = run_backtest(df, np.zeros(len(df)), BTConfig())
    assert np.allclose(res.equity, 1.0) and res.n_trades == 0 and len(res.trades) == 0


def test_always_long_equals_buy_and_hold_from_first_fill():
    df = synth_ohlcv(400, seed=2)
    sig = np.zeros(len(df))
    sig[0] = 1
    res = run_backtest(df, sig, BTConfig(fee_bps=0, slip_bps=0))
    assert math.isclose(res.equity.iloc[-1], df["close"].iloc[-1] / df["open"].iloc[1], rel_tol=1e-12)
    assert res.pos.iloc[0] == 0 and (res.pos.iloc[1:] == 1).all()


def test_long_only_round_trip_with_costs_closed_form():
    df = synth_ohlcv(50, seed=3)
    sig = np.zeros(len(df))
    sig[3], sig[7] = 1, -1                                             # long-only: enter @open4, exit @open8
    cfg = BTConfig(fee_bps=5, slip_bps=3, side="long")
    res = run_backtest(df, sig, cfg)
    c = 8e-4
    expect = df["open"].iloc[8] / df["open"].iloc[4] * (1 - c) ** 2
    assert math.isclose(res.equity.iloc[-1], expect, rel_tol=1e-12)
    assert res.n_trades == 1 and res.trades["bars"].iloc[0] == 4


def test_trade_log_returns_sum_to_equity_log_exactly():
    df = synth_ohlcv(3000, seed=5)
    rng = np.random.default_rng(9)
    sig = np.where(rng.random(len(df)) < 0.02, rng.choice([-1, 1], len(df)), 0)
    for cfg in (BTConfig(), BTConfig(leverage=2.0, side="long"), BTConfig(side="short", delay=3)):
        res = run_backtest(df, sig, cfg)
        assert math.isclose(np.log1p(res.trades["ret"]).sum(), np.log(res.equity.iloc[-1]), abs_tol=1e-9)


def test_delay_guard_and_no_peeking_in_engine():
    df = synth_ohlcv(300, seed=4)
    try:
        run_backtest(df, np.zeros(len(df)), BTConfig(delay=0))
        raise AssertionError("delay=0 must raise")
    except ValueError:
        pass
    rng = np.random.default_rng(2)
    sig = np.where(rng.random(len(df)) < 0.05, rng.choice([-1, 1], len(df)), 0)
    a = run_backtest(df, sig, BTConfig()).equity.to_numpy()
    sig2 = sig.copy()
    sig2[150] = -sig2[150] if sig2[150] else 1
    b = run_backtest(df, sig2, BTConfig()).equity.to_numpy()
    assert np.array_equal(a[:151], b[:151])                            # a signal at close t cannot touch bars <= t


def test_target_position_forward_fills_and_filters_side():
    s = np.array([0, 1, 0, 0, -1, 0, 1])
    assert list(target_position(s, "both")) == [0, 1, 1, 1, -1, -1, 1]
    assert list(target_position(s, "long")) == [0, 1, 1, 1, 0, 0, 1]
    assert list(target_position(s, "short")) == [0, 0, 0, 0, -1, -1, 0]


# ----------------------------------------------------------------------------- statistics
def test_expected_max_sharpe_matches_monte_carlo():
    rng = np.random.default_rng(0)
    var, N = 0.0004, 50
    mc = rng.normal(0, math.sqrt(var), (20000, N)).max(axis=1).mean()
    assert abs(expected_max_sharpe(var, N) - mc) / mc < 0.08


def test_dsr_bounded_and_monotone_in_edge():
    rng = np.random.default_rng(1)
    srs = rng.normal(0, 0.02, 40)
    lo = rng.normal(0.0000, 0.01, 4000)
    hi = rng.normal(0.0010, 0.01, 4000)
    d_lo, d_hi = deflated_sharpe(lo, srs), deflated_sharpe(hi, srs)
    assert 0 <= d_lo["dsr"] <= 1 and 0 <= d_hi["dsr"] <= 1 and d_hi["dsr"] > d_lo["dsr"]


def test_zero_cost_null_has_no_leak_signature_and_a_peek_is_detected():
    """Martingale prices => a causal strategy has zero expected PnL. A 1-bar peek must light up (~Sharpe 3)."""
    def sh(df, sig, cfg):
        r = run_backtest(df, sig, cfg, want_trades=False).ret.to_numpy()
        return perf(r, periods_per_year(df.index))["sharpe"]

    cfg = BTConfig(fee_bps=0, slip_bps=0)
    honest, leaky = [], []
    for s in range(300, 330):
        df = synth_ohlcv(8000, seed=s)
        sig = trend_magic(df, TMParams())["sig"]
        honest.append(sh(df, sig.to_numpy(), cfg))
        leaky.append(sh(df, sig.shift(-1).fillna(0).to_numpy(), cfg))
    assert np.mean(honest) < 0.5, np.mean(honest)
    assert np.mean(leaky) > 1.5, np.mean(leaky)


GRID = {"cci_len": [14, 30], "atr_len": [5, 14], "atr_mult": [1.0, 2.0, 3.0], "flip_on": ["wick", "close"]}


def test_null_experiment_best_of_n_is_not_significant():
    df = synth_ohlcv(12_000, seed=21, trend_strength=0.0)
    table, R = sweep(df, GRID)
    best = int(table["sharpe"].idxmax())
    d = deflated_sharpe(R[best].to_numpy(), table["sr_bar"].to_numpy())
    assert d["dsr"] < 0.95, d


def test_power_experiment_planted_trend_is_detected():
    df = synth_ohlcv(12_000, seed=21, trend_strength=0.35)
    table, R = sweep(df, GRID)
    best = int(table["sharpe"].idxmax())
    d = deflated_sharpe(R[best].to_numpy(), table["sr_bar"].to_numpy())
    assert table["sharpe"].max() > 1.0 and d["dsr"] > 0.95, (table["sharpe"].max(), d)
    oos, _ = walk_forward(R, 3000, 1000)
    assert perf(oos, periods_per_year(df.index))["sharpe"] > 0.5


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:  # noqa: BLE001
                fails += 1
                print(f"FAIL {name}: {type(e).__name__}: {e}")
    sys.exit(1 if fails else 0)
