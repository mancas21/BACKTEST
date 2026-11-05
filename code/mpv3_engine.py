#!/usr/bin/env python
"""
mpv3_engine.py — Institutional adapter engine for MP-STRAT-21..40 (claude_mp20_v3).

Specialised focus on the top candidate:
  MP-V3-S10: 'Pure Equal Weight Momentum' (Weekly Rebalance, 20-Day Momentum Filter)

Execution contract:
- Zero-lookahead: signal evaluated at bar t close, rebalanced at bar t+1 OPEN.
- Fee and slippage applied on every dollar of turnover.
- Fully deterministic: universe iterated in strict alphabetical order.
- Computes complete institutional quant scorecard metrics:
  Sharpe, Sortino, Calmar, MaxDD, Win Rate, Profit Factor,
  Serial correlation (trades_pnl list), Concentration (top-5 share and net without top-5),
  Zero-cost control drag_pp, Benchmark comparison, BTC Alpha & Beta,
  Period splits (H1 vs H2), and Calendar Year breakdown.
"""
from __future__ import annotations

import os
from typing import Any
import numpy as np
import pandas as pd

STARTING_EQUITY = 100_000.0
BARS_PER_YEAR = 8760  # 24 * 365

COST_PRESETS = {
    "repo": {"taker_fee": 0.0005, "slippage_bps": 0.00005},      # 5.0 bps fee + 0.5 bps slip = 11 bps RT
    "stress": {"taker_fee": 0.0010, "slippage_bps": 0.00010},    # 10.0 bps fee + 1.0 bps slip = 22 bps RT
    "author": {"taker_fee": 0.0005, "slippage_bps": 0.00030},    # 5.0 bps fee + 3.0 bps slip = 16 bps RT
    "zero": {"taker_fee": 0.0000, "slippage_bps": 0.00000},      # Zero-cost control pass
}

UNIVERSE = ["AVAXUSDT", "BTCUSDT", "ETHUSDT", "LINKUSDT", "SOLUSDT"]


def load_universe_data(paths: list[str]) -> dict[str, pd.DataFrame]:
    """Load CSVs, parse UTC open_ts, align on common sorted index."""
    raw = {}
    for p in paths:
        base = os.path.basename(p)
        sym = base.split("_")[0]
        df = pd.read_csv(p)
        df.columns = [c.strip().lower() for c in df.columns]
        if "open_ts" in df.columns:
            ts = df["open_ts"]
        elif "timestamp" in df.columns:
            ts = df["timestamp"]
        else:
            raise ValueError(f"No timestamp column in {p}")

        if np.issubdtype(ts.dtype, np.number):
            unit = "ms" if ts.iloc[0] > 1e12 else "s"
            idx = pd.to_datetime(ts, unit=unit, utc=True)
        else:
            idx = pd.to_datetime(ts, utc=True)

        df = df.set_index(idx)[["open", "high", "low", "close", "volume"]].sort_index()
        df = df[~df.index.duplicated(keep="first")]
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["open", "high", "low", "close"])
        raw[sym] = df

    # Find common sorted intersection
    common_idx = raw[UNIVERSE[0]].index
    for s in UNIVERSE[1:]:
        if s in raw:
            common_idx = common_idx.intersection(raw[s].index)
    common_idx = common_idx.sort_values()

    return {s: raw[s].loc[common_idx] for s in UNIVERSE if s in raw}


def _run_s10_core(data: dict[str, pd.DataFrame],
                  rebal_bars: int = 168,
                  mom_bars: int = 480,
                  fee: float = 0.0005,
                  slip: float = 0.00005,
                  starting_equity: float = STARTING_EQUITY) -> dict[str, Any]:
    """Run deterministic zero-lookahead backtest for MP-V3-S10."""
    pairs = sorted(list(data.keys()))
    idx = next(iter(data.values())).index
    n = len(idx)

    cash = float(starting_equity)
    holdings = {p: 0.0 for p in pairs}
    equity = np.zeros(n, dtype=np.float64)
    pending_target: dict[str, float] | None = None

    period_pnls: list[float] = []
    rebal_records: list[dict[str, Any]] = []
    last_val = float(starting_equity)
    total_fees = 0.0
    total_slip = 0.0
    total_turnover = 0.0

    for t in range(n):
        opens = {p: float(data[p]["open"].iat[t]) for p in pairs}
        closes = {p: float(data[p]["close"].iat[t]) for p in pairs}

        # Step 1: Execute Pending Rebalance at bar t OPEN
        if pending_target is not None:
            port_open = cash + sum(holdings[p] * opens[p] for p in pairs)
            pnl_period = port_open - last_val
            period_pnls.append(float(pnl_period))
            last_val = port_open

            turnover_this_bar = 0.0
            rebal_rec = {"bar": t, "timestamp": str(idx[t]), "portfolio_val": port_open, "allocations": {}}

            for p in pairs:
                target_w = pending_target.get(p, 0.0)
                rebal_rec["allocations"][p] = target_w
                target_units = (target_w * port_open) / opens[p] if opens[p] > 0 else 0.0
                delta_units = target_units - holdings[p]
                if abs(delta_units) > 1e-8:
                    trade_dir = 1.0 if delta_units > 0 else -1.0
                    fill_price = opens[p] * (1.0 + trade_dir * slip)
                    notional = abs(delta_units) * fill_price
                    fee_paid = notional * fee
                    slip_cost = abs(fill_price - opens[p]) * abs(delta_units)

                    cash -= delta_units * fill_price + fee_paid
                    holdings[p] = target_units

                    total_fees += fee_paid
                    total_slip += slip_cost
                    turnover_this_bar += notional

            total_turnover += turnover_this_bar
            rebal_records.append(rebal_rec)
            pending_target = None

        # Step 2: Mark-to-market at bar t CLOSE
        port_close = cash + sum(holdings[p] * closes[p] for p in pairs)
        equity[t] = port_close

        # Step 3: Evaluate Signal at bar t CLOSE (eligible for execution at t+1 OPEN)
        if t >= mom_bars and t % rebal_bars == 0:
            eligible = []
            for p in pairs:
                c_now = float(data[p]["close"].iat[t])
                c_past = float(data[p]["close"].iat[t - mom_bars])
                if c_past > 0 and (c_now / c_past - 1.0) > 0.0:
                    eligible.append(p)

            if not eligible:
                pending_target = {p: 0.0 for p in pairs}
            else:
                w = 1.0 / len(eligible)
                pending_target = {p: (w if p in eligible else 0.0) for p in pairs}

    # Final period pnl up to end of data
    final_val = float(equity[-1])
    final_period_pnl = final_val - last_val
    period_pnls.append(float(final_period_pnl))

    return {
        "equity": equity,
        "index": idx,
        "period_pnls": period_pnls,
        "rebal_records": rebal_records,
        "total_fees": total_fees,
        "total_slip": total_slip,
        "total_turnover": total_turnover,
    }


def run_mpv3(paths: list[str], params: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str], list[dict[str, Any]]]:
    """Harness entrypoint for vrun.py."""
    data_all = load_universe_data(paths)
    window = params.get("window", "full")
    cost_name = params.get("costs", "repo")
    mom_bars = int(params.get("mom_bars", 480))
    rebal_bars = int(params.get("rebal_bars", 168))

    costs = COST_PRESETS.get(cost_name, COST_PRESETS["repo"])
    fee = costs["taker_fee"]
    slip = costs["slippage_bps"]

    # Slice data according to window
    n_full = len(next(iter(data_all.values())))
    if window == "last6mo":
        # 6 months ~ 4,368 bars + 2,400 warmup = 6,768 bars
        cut = max(0, n_full - 6768)
        data = {p: df.iloc[cut:].copy() for p, df in data_all.items()}
    elif window == "wf_is":
        # 2020 through 2023
        data = {p: df[df.index.year <= 2023].copy() for p, df in data_all.items()}
    elif window == "wf_oos":
        # 2024 through 2026 (with 480 bars warmup from 2023)
        idx_2024 = data_all[UNIVERSE[0]].index >= "2024-01-01"
        first_2024_pos = int(np.where(idx_2024)[0][0])
        warmup_start = max(0, first_2024_pos - mom_bars)
        data = {p: df.iloc[warmup_start:].copy() for p, df in data_all.items()}
    else:
        data = data_all

    idx = next(iter(data.values())).index
    n = len(idx)

    # 1. Run Costed Backtest
    res = _run_s10_core(data, rebal_bars=rebal_bars, mom_bars=mom_bars, fee=fee, slip=slip)
    equity = res["equity"]
    period_pnls = res["period_pnls"]

    # 2. Run Zero-Cost Control Backtest
    res_zero = _run_s10_core(data, rebal_bars=rebal_bars, mom_bars=mom_bars, fee=0.0, slip=0.0)
    ret_zero_pct = float(res_zero["equity"][-1] / STARTING_EQUITY - 1.0) * 100.0

    # 3. Compute Equal-Weight Buy-and-Hold Benchmark
    pairs = sorted(list(data.keys()))
    bh_holdings = {p: (STARTING_EQUITY / len(pairs)) / data[p]["open"].iat[0] for p in pairs}
    bh_curve = np.zeros(n, dtype=np.float64)
    for t in range(n):
        bh_curve[t] = sum(bh_holdings[p] * data[p]["close"].iat[t] for p in pairs)

    bench_ret_pct = float(bh_curve[-1] / STARTING_EQUITY - 1.0) * 100.0
    bench_peak = np.maximum.accumulate(bh_curve)
    bench_dd_pct = float(((bh_curve - bench_peak) / bench_peak).min()) * 100.0

    # 4. Core Performance Metrics
    final_eq = float(equity[-1])
    return_pct = float(final_eq / STARTING_EQUITY - 1.0) * 100.0
    drag_pp = float(ret_zero_pct - return_pct)

    peak = np.maximum.accumulate(equity)
    drawdowns = (equity - peak) / peak
    max_dd_pct = float(drawdowns.min()) * 100.0

    # Hourly returns for Sharpe & Sortino
    eq_series = pd.Series(equity, index=idx)
    hourly_rets = eq_series.pct_change().dropna()
    mean_ret = float(hourly_rets.mean())
    std_ret = float(hourly_rets.std())
    sharpe = float(mean_ret / (std_ret + 1e-12) * np.sqrt(BARS_PER_YEAR))

    downside = hourly_rets[hourly_rets < 0.0]
    downside_std = float(downside.std()) if len(downside) > 1 else std_ret
    sortino = float(mean_ret / (downside_std + 1e-12) * np.sqrt(BARS_PER_YEAR))

    years = max(0.1, n / BARS_PER_YEAR)
    cagr = float((final_eq / STARTING_EQUITY) ** (1.0 / years) - 1.0) * 100.0
    calmar = float(cagr / abs(max_dd_pct)) if abs(max_dd_pct) > 1e-4 else 0.0

    # Profit Factor & Win Rate on rebalance periods
    wins = [float(p) for p in period_pnls if p > 0]
    losses = [float(p) for p in period_pnls if p < 0]
    gross_profit = float(sum(wins))
    gross_loss = float(abs(sum(losses)))
    profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else 999.0
    win_rate = float(len(wins) / len(period_pnls) * 100.0) if period_pnls else 0.0

    # Concentration Metrics
    sorted_pnls = sorted(period_pnls, reverse=True)
    top5_sum = float(sum(sorted_pnls[:5]))
    total_pnl = float(final_eq - STARTING_EQUITY)
    conc_top5_share_pct = float(top5_sum / total_pnl * 100.0) if total_pnl > 0 else 0.0
    conc_net_without_top5_pct = float((total_pnl - top5_sum) / STARTING_EQUITY * 100.0)

    # BTC Alpha and Beta
    btc_series = data.get("BTCUSDT")
    if btc_series is not None:
        btc_rets = btc_series["close"].pct_change().dropna()
        common_rets_idx = hourly_rets.index.intersection(btc_rets.index)
        y = hourly_rets.loc[common_rets_idx].values
        x = btc_rets.loc[common_rets_idx].values
        cov_matrix = np.cov(y, x)
        beta = float(cov_matrix[0, 1] / max(cov_matrix[1, 1], 1e-12))
        r_squared = float((cov_matrix[0, 1] ** 2) / max(cov_matrix[0, 0] * cov_matrix[1, 1], 1e-12))
        ann_btc_ret = float(np.mean(x) * BARS_PER_YEAR)
        ann_strat_ret = float(np.mean(y) * BARS_PER_YEAR)
        alpha_pct = float((ann_strat_ret - beta * ann_btc_ret) * 100.0)
    else:
        beta, r_squared, alpha_pct = 0.0, 0.0, 0.0

    # Period Split: First Half (H1) vs Second Half (H2)
    half_pt = n // 2
    eq_h1 = equity[:half_pt]
    eq_h2 = equity[half_pt:]
    ret_h1_pct = float(eq_h1[-1] / eq_h1[0] - 1.0) * 100.0
    ret_h2_pct = float(eq_h2[-1] / eq_h2[0] - 1.0) * 100.0

    pnls_h1 = period_pnls[: len(period_pnls) // 2]
    pnls_h2 = period_pnls[len(period_pnls) // 2 :]
    w_h1, l_h1 = [p for p in pnls_h1 if p > 0], [abs(p) for p in pnls_h1 if p < 0]
    w_h2, l_h2 = [p for p in pnls_h2 if p > 0], [abs(p) for p in pnls_h2 if p < 0]
    pf_h1 = float(sum(w_h1) / sum(l_h1)) if sum(l_h1) > 0 else 999.0
    pf_h2 = float(sum(w_h2) / sum(l_h2)) if sum(l_h2) > 0 else 999.0

    # 5. Build Calendar Year Tables
    calendar_years = sorted(list(set(idx.year)))
    tables = []
    bh_s = pd.Series(bh_curve, index=idx)
    for y in calendar_years:
        sub_eq = eq_series[eq_series.index.year == y]
        sub_bh = bh_s[bh_s.index.year == y]
        if len(sub_eq) > 10:
            y_ret = float(sub_eq.iloc[-1] / sub_eq.iloc[0] - 1.0) * 100.0
            y_bh = float(sub_bh.iloc[-1] / sub_bh.iloc[0] - 1.0) * 100.0
            y_peak = np.maximum.accumulate(sub_eq.values)
            y_dd = float(((sub_eq.values - y_peak) / y_peak).min()) * 100.0
            tables.append({
                "year": int(y),
                "return_pct": round(y_ret, 2),
                "benchmark_return_pct": round(y_bh, 2),
                "max_dd_pct": round(y_dd, 2),
                "bars": int(len(sub_eq)),
            })

    # 6. Statistical tests from quant_metrics
    import quant_metrics as qm
    lb = qm.ljung_box_test(period_pnls, lags=10) if len(period_pnls) > 12 else {}
    boot = qm.block_bootstrap(period_pnls, draws=20000, seed=7) if len(period_pnls) > 10 else {}

    # Assemble Institutional Metrics dictionary
    metrics: dict[str, Any] = {
        "strategy": "MP-V3-S10",
        "name": "Pure Equal Weight Momentum",
        "window": window,
        "costs": cost_name,
        "bars": n,
        "rebal_hours": rebal_bars,
        "rebal_days": rebal_bars // 24,
        "mom_hours": mom_bars,
        "mom_days": mom_bars // 24,
        "fee_bps": round(fee * 10000.0, 1),
        "slip_bps": round(slip * 10000.0, 1),
        "rt_bps": round((fee + slip) * 20000.0, 1),
        "span_years": round(n / BARS_PER_YEAR, 2),
        "start_utc": str(idx[0]),
        "end_utc": str(idx[-1]),
        "return_pct": round(return_pct, 4),
        "cagr_pct": round(cagr, 4),
        "profit_factor": round(profit_factor, 4),
        "sharpe": round(sharpe, 4),
        "sharpe_annualized": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "sortino_annualized": round(sortino, 4),
        "calmar": round(calmar, 4),
        "calmar_ratio": round(calmar, 4),
        "max_dd_pct": round(max_dd_pct, 4),
        "n_trades": len(period_pnls),
        "win_rate": round(win_rate, 2),
        "win_rate_pct": round(win_rate, 2),
        "fees_paid": round(res["total_fees"], 2),
        "slippage_paid": round(res["total_slip"], 2),
        "turnover_notional": round(res["total_turnover"], 2),
        "cost_drag_pp": round(drag_pp, 4),
        "conc_top5_share_pct": round(conc_top5_share_pct, 2),
        "conc_net_without_top5_pct": round(conc_net_without_top5_pct, 2),
        "bench_ret_pct": round(bench_ret_pct, 4),
        "bench_dd_pct": round(bench_dd_pct, 4),
        "alpha_pct": round(alpha_pct, 4),
        "beta": round(beta, 4),
        "r2": round(r_squared, 4),
        "h1_return_pct": round(ret_h1_pct, 4),
        "h2_return_pct": round(ret_h2_pct, 4),
        "h1_pf": round(pf_h1, 4),
        "h2_pf": round(pf_h2, 4),
        "min_margin_buffer_pct": 100.0,
        "max_gross_leverage": 1.0,
        "max_leverage_reached": 1.0,
        "bars_over_leverage": 0,
        "liquidation_occurred": False,
        "lb_q_stat": round(float(lb.get("q_stat", 0.0)), 4) if lb else None,
        "lb_p_val": round(float(lb.get("p_val", 1.0)), 4) if lb else None,
        "boot_mean": round(float(boot.get("mean", 0.0)), 4) if boot else None,
        "boot_ci_lo": round(float(boot.get("ci_lo", 0.0)), 4) if boot else None,
        "boot_ci_hi": round(float(boot.get("ci_hi", 0.0)), 4) if boot else None,
        "boot_t_stat": round(float(boot.get("t_stat", 0.0)), 4) if boot else None,
        "boot_p_le_zero": round(float(boot.get("p_le_zero", 0.0)), 4) if boot else None,
        "closed_pnl": [round(p, 2) for p in period_pnls],
        "trades_pnl": [round(p, 2) for p in period_pnls],
        "equity_curve": [round(float(x), 2) for x in equity[::24]],
    }

    provenance = {
        "adapter": "mpv3",
        "engine_version": "mpv3-1",
        "author": "Antigravity Quant Team",
    }

    return metrics, provenance, tables
