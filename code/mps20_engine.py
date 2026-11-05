#!/usr/bin/env python
"""MPS20 -- adapter runner for the "CLAUDE BOT STRATEGIES 1" 20-strategy suite.

Author code ships as `code/claude_bot_1/{engine_core.py,strategies.py}`.
This runner IMPORTS it (no byte edits) and adds what the harness contract needs.
DETERMINISM FIX (2026-10-23, one class only): same-bar candidate SETS were
iterated in process-dependent (PYTHONHASHSEED) order in sig_01, sig_11 and
sig_14, reordering same-bar fills and making float sums diverge in the last
bits across processes (every artifact verify-REFUSED before the fix). The sets
were replaced with the ranked lists they came from; ties in max()/min()
resolve to the first pair in ranked order. No signal thresholds or sizing
changed; code/_claude_audit.py passes 7/7 on the fixed bytes. An OK `verify`
re-runs the engine in a fresh process and is therefore the cross-process
determinism proof for every artifact below.

CONFIGS  params["config"]:
  c5 = the author's SHIPPED universe keys (USDC literals: SOLUSDC, BTCUSDC,
       ETHUSDC, AVAXUSDC, LINKUSDC), fed with repo USDT 1h prices. The
       USDC/USDT basis is bps-level at 1h -- declared proxy, not a quote change.
       This config makes MP-05/MP-10 trade for the first time (they index the
       USDC literals directly; under the prior session's USDT config they
       silently returned 0 trades).
  c4 = the prior 2026-09-26 config (BTCUSDT/ETHUSDT/SOLUSDT/XRPUSDT), parity
       reference. MP-05/MP-10 have explicit "not in data -> no trade" guards;
       they are, on purpose, structurally dead here.

WINDOWS  params["window"]:
  full    = score the ENTIRE aligned intersection from data start.
  last6mo = the engine runs on the last 2,400 warmup bars + 4,368 scored bars;
            every metric is computed on the scored tail only (indices
            >= score_from). Warmup lets atr_pct_norm (1,440), mom_30d (720),
            coint window (2,160) settle without counting as performance.
            Caveat (documented): restarting the EMA stack on the slice re-bases
            span<=200 EMAs / ewm indicators on the warmup segment; at 2,400
            bars the residual is ~e^-12, negligible.

COSTS    params["costs"]: "author" = engine's shipped 5 bps fee + 3 bps slip
per side; "repo6x5" = repo standard 6 bps fee + 5 bps slip per side.
EVERY artifact also runs a ZERO-COST control pass of the same 20 strategies on
the same aligned data and measures the cost drag inside the artifact (drag_pp
= ret_zero - ret_costed, per strategy) -- the cbpackf funding_drag_pp pattern.
The zero-cost pass is a control, not a headline.

STRICT PF  the engine records per-trade PnL net of the EXIT fee only (the
entry fee is debited from cash but not written to the trade record). For every
discrete strategy, the runner recomputes per-trade PnL net of BOTH legs' fees
-> `pf_strict`. GATES READ pf_strict (discrete). Weight-mode "pf" is on
rebalance periods, which already pay fees on both sides.

CONCENTRATION  top-5 best closed trades (discrete) / best-5 rebalance periods
(weight) as a share of total PnL, plus total PnL without them (strict PnL,
discrete). Names follow the cbpackf convention.

Also measured per strategy: period split (two halves of the scored region:
PF + return + n each), per-calendar-year returns (scored spans of 2+ years),
beat-the-equal-weight-benchmark flag, win rate, trade count, fees over gross.
"""
from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_DIR = os.path.join(HERE, "claude_bot_1")
STARTING_EQUITY = 100_000.0
BARS_PER_YEAR = 24 * 365

WARMUP_BARS = 2400
SCORE_BARS = 4368  # the spec's 6-month window at 1h

COST_PRESETS = {
    "author": {"taker_fee": 0.0005, "slippage": 0.0003},
    "repo6x5": {"taker_fee": 0.0006, "slippage": 0.0005},
}

PAIR_CONFIGS = {
    "c5": {
        "keys": ["SOLUSDC", "BTCUSDC", "ETHUSDC", "AVAXUSDC", "LINKUSDC"],
        "src": ["SOLUSDT", "BTCUSDT", "ETHUSDT", "AVAXUSDT", "LINKUSDT"],
    },
    "c4": {
        "keys": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"],
        "src": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"],
    },
}


def load_author_modules():
    """Import the author's engine; strategies.py's
    `from engine_core import StrategyConfig` must resolve to the SAME module."""
    spec = importlib.util.spec_from_file_location(
        "engine_core", os.path.join(ENGINE_DIR, "engine_core.py"))
    ec = importlib.util.module_from_spec(spec)
    sys.modules["engine_core"] = ec
    spec.loader.exec_module(ec)

    spec2 = importlib.util.spec_from_file_location(
        "mps20_author_strategies", os.path.join(ENGINE_DIR, "strategies.py"))
    sg = importlib.util.module_from_spec(spec2)
    sys.modules["mps20_author_strategies"] = sg
    spec2.loader.exec_module(sg)
    return ec, sg


def set_costs(ec, taker: float, slip: float) -> None:
    ec.TAKER_FEE = float(taker)
    ec.SLIPPAGE_BPS = float(slip)


def load_csvs(paths: dict[str, str], keys: list[str], srcs: list[str]) -> dict:
    raw = {}
    for key, src in zip(keys, srcs):
        p = paths[src]
        df = pd.read_csv(p)
        df.columns = [c.strip().lower() for c in df.columns]
        required = ["open_ts", "open", "high", "low", "close", "volume"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"{p} missing columns {missing}")
        idx = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
        df = df.set_index(idx)[required[1:]].sort_index()
        df = df[~df.index.duplicated(keep="first")]
        raw[key] = df
    return raw


def _pf(pnls: list[float]):
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    n = len(pnls)
    if n == 0:
        return None, None, 0, gp, gl
    return (gp / gl if gl > 0 else None), (len(wins) / n), n, gp, gl


def _years(idx: pd.DatetimeIndex, sf: int):
    return sorted({int(y) for y in idx[sf:].year})


def _year_returns(win: pd.Series, idx: pd.DatetimeIndex, sf: int, min_years: int = 2):
    years = _years(idx, sf)
    if len(years) < min_years:
        return None
    out = []
    yr = np.asarray(idx[sf:].year)  # Index==scalar yields ndarray in pandas 2.x
    for y in years:
        sub = win[yr == y]
        if len(sub) >= 2 and sub.iloc[0] != 0:
            out.append({"year": int(y), "ret_pct": float(sub.iloc[-1] / sub.iloc[0] - 1.0) * 100.0})
    return out or None


def _conc_top5(pnls: list[float]) -> tuple:
    total = sum(pnls)
    if len(pnls) >= 5 and total != 0:
        top5 = sorted(pnls, reverse=True)[:5]
        return (100.0 * sum(top5) / total,
                100.0 * (total - sum(top5)) / STARTING_EQUITY)
    return None, None


def _size_of(tr, cfg, indicators) -> float:
    """The engine does not store size in the Trade record, but it formed
    size = risk_amount / (atr_stop_mult * atr14[pair].iat[entry_bar]) at entry;
    reconstruct that exactly (risk_amount is stored)."""
    atr = indicators[tr.pair]["atr14"].iat[tr.entry_bar]
    return tr.risk_amount / (cfg.atr_stop_mult * float(atr))


def score_result(cfg, res, eq_bench, sf: int, taker_fee: float, indicators=None) -> dict:
    eq = res.equity_curve
    idx = eq.index
    n = len(idx)
    sf = int(sf)
    win = eq.iloc[sf:]
    ret = win.pct_change().dropna()

    ret_pct = float(win.iloc[-1] / win.iloc[0] - 1.0) * 100.0 if len(win) > 1 else None
    sharpe = (float(ret.mean() / ret.std() * np.sqrt(BARS_PER_YEAR))
              if len(ret) > 2 and ret.std() > 0 else None)
    dd = (win / win.cummax() - 1.0).min() if len(win) > 1 else 0.0
    bench_ret = float(eq_bench.iloc[-1] / eq_bench.iloc[sf] - 1.0) * 100.0
    beats = (ret_pct > bench_ret) if ret_pct is not None else False

    row = {
        "id": cfg.id, "name": cfg.name, "mode": cfg.mode,
        "ret_pct": ret_pct, "sharpe": sharpe, "max_dd_pct": float(dd) * 100.0,
        "bench_ret_pct": bench_ret, "beats_bh": bool(beats),
        "score_from": sf, "scored_bars": n - sf,
        "eq_final": float(win.iloc[-1]),
    }
    yret = _year_returns(win, idx, sf)
    if yret:
        row["year_returns"] = yret

    if cfg.mode == "discrete":
        trs = [tr for tr in res.trades if tr.exit_bar >= sf]
        pnls = [tr.pnl for tr in trs]
        # strict: subtract the ENTRY fee the engine leaves out of the trade record
        entry_fees = [abs(tr.entry_price * _size_of(tr, cfg, indicators)) * taker_fee
                      for tr in trs] if indicators is not None else [0.0] * len(trs)
        strict = [p - f for p, f in zip(pnls, entry_fees)]
        pf, wr, ntr, _, _ = _pf(pnls)
        pf_s, wr_s, _, gp_strict, _ = _pf(strict)
        row.update({
            "n_trades": ntr, "pf": pf,
            "win_rate_pct": wr * 100.0 if wr is not None else None,
            "pf_strict": pf_s,
            "win_rate_strict_pct": wr_s * 100.0 if wr_s is not None else None,
            "gross_profit_strict": gp_strict,
        })
        c1, c2 = _conc_top5(strict)
        row["conc_top5_share_pct"], row["conc_net_without_top5_pct"] = c1, c2
        fees_charged = (sum(abs(tr.exit_price * _size_of(tr, cfg, indicators)) for tr in trs)
                        + sum(abs(tr.entry_price * _size_of(tr, cfg, indicators)) for tr in trs)) * taker_fee
        row["fees_charged"] = fees_charged
        row["cost_share_pct"] = (100.0 * fees_charged / gp_strict) if gp_strict > 0 else None

        mid = sf + max(1, (n - sf) // 2)
        h1 = [tr for tr in trs if sf <= tr.exit_bar < mid]
        h2 = [tr for tr in trs if tr.exit_bar >= mid]
        p1 = [tr.pnl - abs(tr.entry_price * _size_of(tr, cfg, indicators)) * taker_fee for tr in h1]
        p2 = [tr.pnl - abs(tr.entry_price * _size_of(tr, cfg, indicators)) * taker_fee for tr in h2]
        pf_h1, _, n1, _, _ = _pf(p1)
        pf_h2, _, n2, _, _ = _pf(p2)
        row.update({"pf_h1": pf_h1, "n_h1": n1, "pf_h2": pf_h2, "n_h2": n2,
                    "ret_h1_pct": float(eq.iloc[mid] / eq.iloc[sf] - 1.0) * 100.0 if mid > sf else None,
                    "ret_h2_pct": float(eq.iloc[-1] / eq.iloc[mid] - 1.0) * 100.0})
    else:  # weight mode: "trades" are rebalance periods; fees paid on every fill
        rb = [b for b, _ in res.trades if b >= sf]
        if len(rb) >= 2:
            bounds = rb + [n - 1]
            ppnl = [eq.iat[bounds[i + 1]] - eq.iat[bounds[i]] for i in range(len(bounds) - 1)]
            pret = [(eq.iat[bounds[i + 1]] / eq.iat[bounds[i]] - 1.0)
                    for i in range(len(bounds) - 1) if eq.iat[bounds[i]] != 0]
            pf, wr, ntr, _, _ = _pf(pret)
            row.update({
                "n_trades": ntr, "pf": pf,
                "win_rate_pct": wr * 100.0 if wr is not None else None,
                "pf_strict": None, "win_rate_strict_pct": None,
            })
            c1, c2 = _conc_top5(ppnl)
            row["conc_top5_share_pct"], row["conc_net_without_top5_pct"] = c1, c2
            row["fees_charged"] = None
            row["cost_share_pct"] = None

            mid = sf + max(1, (n - sf) // 2)
            h1 = [x for x in rb if sf <= x < mid]
            h2 = [x for x in rb if x >= mid]
            b1 = h1 + [mid if mid < n else n - 1]
            b2 = h2 + [n - 1]
            pr1 = [(eq.iat[b1[i + 1]] / eq.iat[b1[i]] - 1.0)
                   for i in range(len(b1) - 1) if eq.iat[b1[i]] != 0] if len(b1) >= 2 else []
            pr2 = [(eq.iat[b2[i + 1]] / eq.iat[b2[i]] - 1.0)
                   for i in range(len(b2) - 1) if eq.iat[b2[i]] != 0] if len(b2) >= 2 else []
            pf_h1, _, _, _, _ = _pf(pr1)
            pf_h2, _, _, _, _ = _pf(pr2)
            row.update({"pf_h1": pf_h1, "n_h1": len(h1), "pf_h2": pf_h2, "n_h2": len(h2),
                        "ret_h1_pct": float(eq.iloc[mid] / eq.iloc[sf] - 1.0) * 100.0 if mid > sf else None,
                        "ret_h2_pct": float(eq.iloc[-1] / eq.iloc[mid] - 1.0) * 100.0})
        else:
            row.update({"n_trades": len(rb), "pf": None, "win_rate_pct": None,
                        "pf_strict": None, "win_rate_strict_pct": None,
                        "conc_top5_share_pct": None, "conc_net_without_top5_pct": None,
                        "fees_charged": None, "cost_share_pct": None,
                        "pf_h1": None, "n_h1": 0, "pf_h2": None, "n_h2": 0,
                        "ret_h1_pct": None, "ret_h2_pct": None})
    return row


def _clean(v):
    if v is None:
        return None
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (float, np.floating)):
        x = float(v)
        return x if np.isfinite(x) else None
    return v


def _zero_ctrl(ec, sg, data, indicators, sf: int) -> dict:
    """Zero-cost control pass, same data, same signals. Returns per-id:
    ret_zero_pct, eq_zero_final, gross_zero (closed-trade gross for discrete,
    rebalance-period gross for weight)."""
    set_costs(ec, 0.0, 0.0)
    out = {}
    for cfg in sg.build_strategies():
        try:
            res = ec.run_backtest(cfg, data, indicators)
            eq = res.equity_curve
            win = eq.iloc[sf:]
            d = {
                "ret_zero_pct": float(win.iloc[-1] / win.iloc[0] - 1.0) * 100.0 if len(win) > 1 else None,
                "eq_zero_final": float(win.iloc[-1]),
            }
            if cfg.mode == "discrete":
                trs = [tr for tr in res.trades if tr.exit_bar >= sf]
                _, _, _, gp0, _ = _pf([tr.pnl for tr in trs])
                d["gross_zero"] = gp0
            else:
                rb = [b for b, _ in res.trades if b >= sf]
                if len(rb) >= 2:
                    bounds = rb + [len(eq) - 1]
                    pp = [eq.iat[bounds[i + 1]] - eq.iat[bounds[i]] for i in range(len(bounds) - 1)]
                    _, _, _, gp0, _ = _pf(pp)
                    d["gross_zero"] = gp0
                else:
                    d["gross_zero"] = None
            out[cfg.id] = d
        except Exception as e:
            out[cfg.id] = {"error": f"{type(e).__name__}: {e}"}
    return out


def run_suite(paths: dict[str, str], params: dict) -> dict:
    cfg_name = params["config"]
    window = params.get("window", "full")
    cost_name = params["costs"]

    if cfg_name not in PAIR_CONFIGS:
        raise ValueError(f"unknown config {cfg_name!r}; expected {sorted(PAIR_CONFIGS)}")
    if window not in ("full", "last6mo"):
        raise ValueError(f"unknown window {window!r}")
    if cost_name not in COST_PRESETS:
        raise ValueError(f"unknown cost preset {cost_name!r}; expected {sorted(COST_PRESETS)}")

    ec, sg = load_author_modules()
    conf = PAIR_CONFIGS[cfg_name]
    raw = load_csvs(paths, conf["keys"], conf["src"])

    data = ec.align_universe(raw)
    n_full = len(next(iter(data.values())))

    if window == "last6mo":
        cut = max(0, n_full - (SCORE_BARS + WARMUP_BARS))
        data = {p: df.iloc[cut:].copy() for p, df in data.items()}
    indicators = ec.precompute_indicators(data)
    bench = ec.build_benchmark(data)

    n = len(next(iter(data.values())))
    sf = max(0, n - SCORE_BARS) if window == "last6mo" else 0
    idx = next(iter(data.values())).index

    bench_ret = float(bench.iloc[-1] / bench.iloc[sf] - 1.0) * 100.0
    bench_dd = float((bench.iloc[sf:] / bench.iloc[sf:].cummax() - 1.0).min()) * 100.0

    costs = COST_PRESETS[cost_name]
    set_costs(ec, costs["taker_fee"], costs["slippage"])
    rows = []
    keep = {}
    for cfg in sg.build_strategies():
        try:
            res = ec.run_backtest(cfg, data, indicators)
            row = score_result(cfg, res, bench, sf, costs["taker_fee"], indicators)
            rows.append(row)
            keep[cfg.id] = row
        except Exception as e:  # record and continue; never kill an artifact on one strategy
            rows.append({"id": cfg.id, "name": cfg.name, "mode": cfg.mode,
                         "error": f"{type(e).__name__}: {e}"})

    zero = _zero_ctrl(ec, sg, data, indicators, sf)
    for r in rows:
        z = zero.get(r.get("id"))
        if not z or "error" in z or "error" in r:
            continue
        r["ret_zero_pct"] = z["ret_zero_pct"]
        r["drag_pp"] = (z["ret_zero_pct"] - r["ret_pct"]
                        if r.get("ret_pct") is not None and z["ret_zero_pct"] is not None else None)
        if r.get("cost_share_pct") is None and z.get("gross_zero") not in (None, 0):
            drag_usd = z["eq_zero_final"] - r.get("eq_final", STARTING_EQUITY)
            r["cost_share_pct"] = 100.0 * drag_usd / z["gross_zero"]

    n_error = len([r for r in rows if "error" in r])
    n_pf_strict_gt_12 = len([r for r in rows if (r.get("pf_strict") or 0) > 1.2])
    n_pf_gt_12 = len([r for r in rows if (r.get("pf") or 0) > 1.2])

    metrics = {
        "config": cfg_name, "window": window, "costs": cost_name,
        "pairs": conf["keys"],
        "aligned_bars_full": n_full,
        "engine_slice_bars": n,
        "warmup_bars": sf if window == "last6mo" else 0,
        "score_from": sf, "scored_bars": n - sf,
        "scored_start": str(idx[sf]), "scored_end": str(idx[-1]),
        "bench_ret_pct": bench_ret, "bench_dd_pct": bench_dd,
        "n_strategies": 20, "n_rows_error": n_error,
        "n_pf_strict_gt_1p2": n_pf_strict_gt_12,
        "n_pf_gt_1p2": n_pf_gt_12,
    }
    tables = [{k: _clean(v) for k, v in r.items()} for r in rows]
    return {"metrics": metrics, "tables": tables}
