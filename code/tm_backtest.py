"""
tm_backtest.py - next-open backtester for Trend Magic + sweep / Deflated Sharpe / walk-forward.

Execution model (conservative, no lookahead)
  * A flip is confirmed at the CLOSE of bar t (it uses that bar's low/high/close).
  * Fill = OPEN of bar t+delay (delay >= 1; delay=1 is TradingView's default).
  * Stop-and-reverse: position in {-1, 0, +1} of equity * leverage, rebalanced each bar (constant leverage).
  * Costs: (fee_bps + slip_bps) per side on traded notional. A flip pays both legs.
  * Equity is exactly decomposable into per-trade log-returns (checked in test_tm.py).

NOT modelled: liquidation / margin, funding (pass a per-bar series to include it), partial fills,
latency beyond `delay`, borrow, order-book impact. Keep leverage <= ~3.
"""
from __future__ import annotations

import argparse
import itertools
import math
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd
from scipy import stats

from tm_core import TMParams, trend_magic
from tm_data import load_ohlcv, synth_ohlcv

EULER = 0.5772156649015329


# --------------------------------------------------------------------------------------
# Engine
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class BTConfig:
    fee_bps: float = 5.0      # Binance USDT-M VIP0 taker
    slip_bps: float = 2.0
    leverage: float = 1.0
    side: str = "both"        # both | long | short
    delay: int = 1

    def validate(self) -> None:
        if self.delay < 1:
            raise ValueError("delay must be >= 1: a flip needs the bar's high/low/close, "
                             "so the earliest fill is the NEXT bar's open")
        if self.side not in ("both", "long", "short"):
            raise ValueError("side must be both/long/short")
        if self.leverage <= 0 or self.fee_bps < 0 or self.slip_bps < 0:
            raise ValueError("leverage > 0 and non-negative costs required")


@dataclass
class BTResult:
    ret: pd.Series
    equity: pd.Series
    pos: pd.Series
    trades: pd.DataFrame | None
    n_trades: int


def target_position(sig, side: str) -> np.ndarray:
    s = pd.Series(np.asarray(sig, dtype=float)).replace(0.0, np.nan).ffill().fillna(0.0).to_numpy()
    if side == "long":
        s = np.maximum(s, 0.0)
    elif side == "short":
        s = np.minimum(s, 0.0)
    return s


def run_backtest(df: pd.DataFrame, sig, cfg: BTConfig | None = None, funding: pd.Series | None = None,
                 want_trades: bool = True) -> BTResult:
    cfg = cfg or BTConfig()
    cfg.validate()
    o, c = df["open"].to_numpy(np.float64), df["close"].to_numpy(np.float64)
    n, d, lev = len(c), cfg.delay, cfg.leverage

    tgt = target_position(sig, cfg.side)
    pos = np.zeros(n)
    if n > d:
        pos[d:] = tgt[: n - d]                       # decided at close t-d, held from open t
    pprev = np.r_[0.0, pos[:-1]]
    gap = o / np.r_[o[0], c[:-1]] - 1.0              # close[t-1] -> open[t], held by pos[t-1]
    intra = c / o - 1.0                              # open[t] -> close[t], held by pos[t]

    cost = (cfg.fee_bps + cfg.slip_bps) * 1e-4 * lev
    changed = pos != pprev
    exit_c = np.where(changed, np.abs(pprev) * cost, 0.0)
    entry_c = np.where(changed, np.abs(pos) * cost, 0.0)
    fund = np.zeros(n) if funding is None else funding.reindex(df.index).fillna(0.0).to_numpy(np.float64)

    def lg(x):
        return np.log(np.clip(x, 1e-12, None))

    La, Lx = lg(1 + lev * pprev * gap), lg(1 - exit_c)
    Le, Li, Lf = lg(1 - entry_c), lg(1 + lev * pos * intra), lg(1 - lev * pos * fund)
    logret = La + Lx + Le + Li + Lf
    ret = pd.Series(np.expm1(logret), index=df.index, name="ret")
    equity = pd.Series(np.exp(np.cumsum(logret)), index=df.index, name="equity")

    starts = (pos != 0) & changed
    n_trades = int(starts.sum())
    trades = None
    if want_trades:
        tid = np.cumsum(starts) - 1
        tid[pos == 0] = -1
        tprev = np.r_[-1, tid[:-1]]
        k = max(n_trades, 1)
        own_now, own_prev = Li + Le + Lf, La + Lx
        m1, m0 = tid >= 0, tprev >= 0
        tl = (np.bincount(tid[m1], weights=own_now[m1], minlength=k)
              + np.bincount(tprev[m0], weights=own_prev[m0], minlength=k))[:n_trades]
        s_idx = np.flatnonzero(starts)
        chg = np.flatnonzero(changed)
        nxt = np.searchsorted(chg, s_idx, side="right")
        is_open = nxt >= len(chg)
        e_idx = np.where(is_open, n - 1, chg[np.minimum(nxt, max(len(chg) - 1, 0))] if len(chg) else n - 1)
        exit_px = np.where(is_open, c[-1], o[e_idx])
        trades = pd.DataFrame({
            "entry_time": df.index[s_idx], "exit_time": df.index[e_idx],
            "side": np.where(pos[s_idx] > 0, "long", "short"),
            "entry_px": o[s_idx], "exit_px": exit_px, "bars": e_idx - s_idx,
            "ret": np.expm1(tl), "open": is_open,
        })
    return BTResult(ret, equity, pd.Series(pos, index=df.index, name="pos"), trades, n_trades)


# --------------------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------------------
def periods_per_year(index: pd.DatetimeIndex) -> float:
    dt = index.to_series().diff().dropna().median().total_seconds()
    return 365.25 * 24 * 3600 / dt


def perf(ret, ppy: float, pos=None, trades: pd.DataFrame | None = None) -> dict:
    r = np.clip(np.asarray(ret, dtype=float), -0.999999, None)
    n = len(r)
    eq = np.exp(np.cumsum(np.log1p(r)))
    mu, sd = r.mean(), r.std(ddof=1)
    years = n / ppy
    peak = np.maximum.accumulate(np.r_[1.0, eq])[1:]
    mdd = float((eq / peak - 1).min())
    cagr = float(eq[-1] ** (1 / years) - 1) if eq[-1] > 0 else -1.0
    dn = math.sqrt(float(np.mean(np.minimum(r, 0.0) ** 2)))
    out = {
        "total_ret": float(eq[-1] - 1), "cagr": cagr,
        "sharpe": float(mu / sd * math.sqrt(ppy)) if sd > 0 else float("nan"),
        "sortino": float(mu / dn * math.sqrt(ppy)) if dn > 0 else float("nan"),
        "vol_ann": float(sd * math.sqrt(ppy)), "max_dd": mdd,
        "calmar": cagr / abs(mdd) if mdd < 0 else float("nan"),
    }
    if pos is not None:
        p = np.asarray(pos, dtype=float)
        out["exposure"] = float(np.mean(p != 0))
        out["turnover_yr"] = float(np.abs(np.diff(p, prepend=0.0)).sum() / years)
    if trades is not None and len(trades):
        w, lo = trades.loc[trades["ret"] > 0, "ret"], trades.loc[trades["ret"] <= 0, "ret"]
        out.update(n_trades=len(trades), win_rate=float((trades["ret"] > 0).mean()),
                   profit_factor=float(w.sum() / abs(lo.sum())) if lo.sum() < 0 else float("inf"),
                   avg_trade=float(trades["ret"].mean()), avg_bars=float(trades["bars"].mean()))
    return out


def buy_hold(df: pd.DataFrame) -> pd.Series:
    """Long from the first open to each close, expressed as per-bar returns."""
    c, o = df["close"].to_numpy(), df["open"].to_numpy()
    r = c / np.r_[o[0], c[:-1]] - 1.0
    return pd.Series(r, index=df.index)


# --------------------------------------------------------------------------------------
# Selection-bias control: Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014)
# --------------------------------------------------------------------------------------
def expected_max_sharpe(var_sr: float, n_trials: int) -> float:
    """E[max of N iid SR estimates] under the null SR=0, for per-bar SR variance var_sr."""
    if n_trials < 2:
        return 0.0
    return math.sqrt(var_sr) * ((1 - EULER) * stats.norm.ppf(1 - 1 / n_trials)
                                + EULER * stats.norm.ppf(1 - 1 / (n_trials * math.e)))


def deflated_sharpe(r, sr_trials) -> dict:
    """
    r         : per-bar returns of the SELECTED config
    sr_trials : per-bar (non-annualised) Sharpe of EVERY config tried (including r's)
    DSR = P(true SR > 0 | best of N trials), non-normality adjusted. Treat < 0.95 as 'not distinguishable
    from the best of N random configs'. Assumes ~iid bars; serial correlation makes it optimistic.
    """
    r = np.asarray(r, float)
    T = len(r)
    sr = r.mean() / r.std(ddof=1)
    sr_trials = np.asarray(sr_trials, float)
    sr_trials = sr_trials[np.isfinite(sr_trials)]
    sr0 = expected_max_sharpe(float(sr_trials.var(ddof=1)), len(sr_trials)) if len(sr_trials) > 1 else 0.0
    g3, g4 = stats.skew(r), stats.kurtosis(r, fisher=False)
    den = math.sqrt(max(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2, 1e-12))
    z = (sr - sr0) * math.sqrt(T - 1) / den
    return {"sr_bar": float(sr), "sr0_bar": float(sr0), "dsr": float(stats.norm.cdf(z)), "T": T,
            "skew": float(g3), "kurt": float(g4), "n_trials": len(sr_trials)}


# --------------------------------------------------------------------------------------
# Sweep + walk-forward
# --------------------------------------------------------------------------------------
DEFAULT_GRID = {
    "cci_len": [14, 20, 30, 50],
    "atr_len": [5, 10, 14],
    "atr_mult": [1.0, 1.5, 2.0, 3.0],
    "flip_on": ["wick", "close"],
}


def sweep(df: pd.DataFrame, grid: dict | None = None, base: TMParams | None = None,
          cfg: BTConfig | None = None, mode: str = "fixed") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (table indexed by config id, per-bar net returns with one column per config id)."""
    grid, base, cfg = grid or DEFAULT_GRID, base or TMParams(), cfg or BTConfig()
    keys = list(grid)
    ppy = periods_per_year(df.index)
    cache: dict = {}
    rows, cols = [], {}
    for i, combo in enumerate(itertools.product(*(grid[k] for k in keys))):
        p = replace(base, **dict(zip(keys, combo)))
        tm = trend_magic(df, p, mode=mode, cache=cache)
        res = run_backtest(df, tm["sig"].to_numpy(), cfg, want_trades=False)
        r = res.ret.to_numpy()
        m = perf(r, ppy, res.pos.to_numpy())
        rows.append({"id": i, **dict(zip(keys, combo)), **m, "n_trades": res.n_trades,
                     "sr_bar": r.mean() / r.std(ddof=1) if r.std(ddof=1) > 0 else float("nan")})
        cols[i] = r
    return pd.DataFrame(rows).set_index("id"), pd.DataFrame(cols, index=df.index)


def walk_forward(R: pd.DataFrame, train_bars: int, test_bars: int, step: int | None = None):
    """
    Rolling WFO over per-bar config returns: pick the best train-Sharpe config, take its NEXT test window.
    Valid because indicator + engine are causal (a config's return at t never uses data after t).
    Stitched OOS ignores the cost of switching configs between windows.
    """
    step = step or test_bars
    Rv, n = R.to_numpy(), len(R)
    oos, picks = [], []
    for s in range(0, n - train_bars - test_bars + 1, step):
        tr = Rv[s: s + train_bars]
        sd = tr.std(axis=0, ddof=1)
        sr = np.where(sd > 0, tr.mean(axis=0) / np.where(sd > 0, sd, 1), -np.inf)
        j = int(np.argmax(sr))
        a, b = s + train_bars, s + train_bars + test_bars
        oos.append(pd.Series(Rv[a:b, j], index=R.index[a:b]))
        picks.append({"test_start": R.index[a], "config": R.columns[j], "train_sr_bar": float(sr[j])})
    if not oos:
        raise ValueError("not enough bars for the requested train/test windows")
    return pd.concat(oos), pd.DataFrame(picks)


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------
def _fmt(d: dict) -> str:
    keys = ["total_ret", "cagr", "sharpe", "sortino", "max_dd", "calmar", "vol_ann", "exposure", "turnover_yr",
            "n_trades", "win_rate", "profit_factor", "avg_trade", "avg_bars"]
    return "  ".join(f"{k}={d[k]:.4g}" if isinstance(d[k], float) else f"{k}={d[k]}" for k in keys if k in d)


def main() -> None:
    ap = argparse.ArgumentParser(description="Trend Magic backtest")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", help="csv/parquet with time + OHLCV")
    src.add_argument("--synthetic", action="store_true", help="synthetic data: MECHANICS ONLY")
    ap.add_argument("--trend-strength", type=float, default=0.0, help="synthetic planted trend (0 = null)")
    ap.add_argument("--n", type=int, default=30_000)
    ap.add_argument("--tf-minutes", type=int, default=60)
    ap.add_argument("--fee-bps", type=float, default=5.0)
    ap.add_argument("--slip-bps", type=float, default=2.0)
    ap.add_argument("--lev", type=float, default=1.0)
    ap.add_argument("--side", default="both", choices=["both", "long", "short"])
    ap.add_argument("--delay", type=int, default=1)
    ap.add_argument("--mode", default="fixed", choices=["fixed", "legacy"])
    ap.add_argument("--sweep", action="store_true", help="grid sweep + DSR + walk-forward")
    ap.add_argument("--wf-train", type=int, default=0, help="train bars (default n/4)")
    ap.add_argument("--wf-test", type=int, default=0, help="test bars (default n/12)")
    a = ap.parse_args()

    df = synth_ohlcv(a.n, a.tf_minutes, trend_strength=a.trend_strength) if a.synthetic else load_ohlcv(a.csv)
    cfg = BTConfig(a.fee_bps, a.slip_bps, a.lev, a.side, a.delay)
    ppy = periods_per_year(df.index)
    print(f"{len(df)} bars  {df.index[0]} -> {df.index[-1]}  ppy={ppy:.0f}  mode={a.mode}")
    if a.synthetic:
        print("[synthetic data: results show mechanics, NOT edge]")

    tm = trend_magic(df, TMParams(), mode=a.mode)
    res = run_backtest(df, tm["sig"].to_numpy(), cfg)
    print("\nstrategy :", _fmt(perf(res.ret, ppy, res.pos, res.trades)))
    print("buy&hold :", _fmt(perf(buy_hold(df), ppy)))

    if a.sweep:
        table, R = sweep(df, cfg=cfg, mode=a.mode)
        top = table.sort_values("sharpe", ascending=False)
        print(f"\n--- sweep: {len(table)} configs (top 8 by Sharpe) ---")
        print(top.head(8)[["cci_len", "atr_len", "atr_mult", "flip_on", "sharpe", "cagr", "max_dd", "n_trades"]]
              .to_string(float_format=lambda x: f"{x:.3f}"))
        best = int(top.index[0])
        d = deflated_sharpe(R[best].to_numpy(), table["sr_bar"].to_numpy())
        print(f"\nbest config id={best}: SR/bar={d['sr_bar']:.5f}  expected-max-under-null SR0/bar={d['sr0_bar']:.5f}"
              f"  DSR={d['dsr']:.3f}  (trials={d['n_trials']}, T={d['T']}, skew={d['skew']:.2f}, kurt={d['kurt']:.1f})")
        tr_b = a.wf_train or len(df) // 4
        te_b = a.wf_test or len(df) // 12
        oos, picks = walk_forward(R, tr_b, te_b)
        print(f"\nwalk-forward OOS (train={tr_b}, test={te_b}, windows={len(picks)}):", _fmt(perf(oos, ppy)))
        print("distinct configs picked:", picks["config"].nunique(), "of", len(table))


if __name__ == "__main__":
    main()
