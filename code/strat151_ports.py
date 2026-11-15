#!/usr/bin/env python
"""strat151_ports.py — adaptadores vrun para las estrategias de la sesión
2026-11-14 (trading-engines/strategies/):

  * capfloor_rotation_v1 — fund-squeeze cross-sectional (funding extremo
    negativo long / positivo short, filtro de dispersión anti-§5.7).
  * smc_structure_rotation_v1 — estado SMC (CHOCH/BOS, port de early-engine/
    smc.py, sin lookahead) como factor rotativo con gate de momento MP-18.

Contrato vrun (patrón run_mp20): run(paths, params) -> (metrics, meta, tables)
con params["window"] en {"FULL","IS","OOS"} (split 70/30 sobre barras).
Una fila por estrategia con el schema estándar de tables.
"""
from __future__ import annotations

import os
import sys

import importlib.util
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _load_module(path: str, name: str):
    """Loader local (vrun._load_module no vive en este modulo)."""
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        m = importlib.util.module_from_spec(spec)
        sys.modules[name] = m
        spec.loader.exec_module(m)
    return sys.modules[name]

DATA = os.path.join(os.path.dirname(HERE), "data")


# ────────────────────────────────────────────── capfloor_rotation_v1 ──
def run_capfloor(paths, params):
    import capfloor_rotation_v1 as C

    params = {**C.PARAMS, **(params or {})}
    close, fund = C.build_matrices(params)
    n = len(close)
    start = params["regime_lookback_bars"] + params["funding_avg_settlements"] * 8

    def run_window(w0: int, w1: int) -> dict:
        w_cur = None
        last_rb = -10**9
        eq = 1.0
        curve = [1.0]
        period_rets = []
        for i in range(w0, w1):
            if w_cur:
                rets = []
                for sym, w in w_cur.items():
                    p0, p1 = close[sym].iloc[i - 1], close[sym].iloc[i]
                    if p0 == p0 and p1 == p1 and p0 > 0:
                        rets.append(w * (p1 / p0 - 1.0))
                if rets:
                    eq *= (1.0 + sum(rets))
            curve.append(eq)
            if i - last_rb >= params["rebalance_bars"]:
                r = curve[-1] / curve[-2] - 1.0 if len(curve) > 1 else 0.0
                period_rets.append(r)
                w_cur = C.weights(close, fund, i, params)
                eq *= (1.0 - params["cost_rt_bps"] / 1e4)
                last_rb = i
        return _summarize(curve, period_rets, w1 - w0)

    win = _windows(n, start)
    metrics, tables = _emit("capfloor", win, run_window, params)
    return metrics, {"adapter": "capfloor", "engine_version": "capfloor-v1"}, tables


# ──────────────────────────────────────────── smc_structure_rotation_v1 ──
def run_smcrot(paths, params):
    import smc_structure_rotation_v1 as S

    params = {**S.PARAMS, **(params or {})}
    closes, events = S.build_states(params)
    n = max(len(c) for c in closes.values())
    start = params["warmup_bars"] + params["momentum_gate_bars"]

    def run_window(w0: int, w1: int) -> dict:
        w_cur = {}
        last_rb = -10**9
        eq = 1.0
        curve = [1.0]
        period_rets = []
        for i in range(w0, w1):
            if w_cur:
                rets = []
                for sym, w in w_cur.items():
                    c = closes[sym]
                    if i < len(c):
                        p0, p1 = c[i - 1], c[i]
                        if p0 > 0 and p1 == p1:
                            rets.append(w * (p1 / p0 - 1.0))
                if rets:
                    eq *= (1.0 + sum(rets))
            curve.append(eq)
            if i - last_rb >= params["rebalance_bars"]:
                r = curve[-1] / curve[-2] - 1.0 if len(curve) > 1 else 0.0
                period_rets.append(r)
                w_cur = S.weights(closes, events, i, params)
                eq *= (1.0 - params["cost_rt_bps"] / 1e4)
                last_rb = i
        return _summarize(curve, period_rets, w1 - w0)

    win = _windows(n, start)
    metrics, tables = _emit("smcrot", win, run_window, params)
    return metrics, {"adapter": "smcrot", "engine_version": "smcrot-v1"}, tables


# ───────────────────────────────────────────── ew_exhaustion_rotation_v1 ──
def run_ewexh(paths, params):
    """EW impulse-exhaustion cross-sectional rotation (sesión 2026-11-15).
    Impulso de 5 ondas COMPLETADO (reglas duras: W4 no solapa W1, W3 no el
    más corto) => reversión por agotamiento, long bajista-completo vs short
    alcista-completo, con invalidación estructural por pierna."""
    M = _load_module(os.path.join(HERE, "ew_exhaustion_rotation_v1.py"),
                     "ew_exhaustion_rotation_v1")
    params = {**M.PARAMS, **(params or {})}
    closes, events = M.build_events(params)
    n = max(len(c) for c in closes.values())
    start = params["warmup_bars"]

    def run_window(w0: int, w1: int) -> dict:
        w_cur = {}
        last_rb = -10**9
        eq = 1.0
        curve = [1.0]
        period_rets = []
        for i in range(w0, w1):
            if w_cur:
                rets = []
                for sym, w in w_cur.items():
                    c = closes[sym]
                    if i < len(c):
                        p0, p1 = c[i - 1], c[i]
                        if p0 > 0 and p1 == p1:
                            rets.append(w * (p1 / p0 - 1.0))
                if rets:
                    eq *= (1.0 + sum(rets))
                curve.append(eq)
                r = curve[-1] / curve[-2] - 1.0 if len(curve) > 1 else 0.0
                period_rets.append(r)
            if i - last_rb >= params["rebalance_bars"]:
                w_cur = M.weights(closes, events, i, params)
                if w_cur:
                    eq *= (1.0 - params["cost_rt_bps"] / 1e4)
                last_rb = i
        return _summarize(curve, period_rets, w1 - w0)

    win = _windows(n, start)
    metrics, tables = _emit("ewexh", win, run_window, params)
    return metrics, {"adapter": "ewexh", "engine_version": "ewexh-v1"}, tables


# ──────────────────────────────────────────────────────── utilidades ──
def _windows(n: int, start: int) -> dict:
    """FULL/IS/OOS con split 70/30 sobre el rango útil."""
    split = start + int((n - start) * 0.70)
    return {"FULL": (start, n), "IS": (start, split), "OOS": (split, n)}


def _summarize(curve: list, period_rets: list, n_bars: int) -> dict:
    series = pd.Series(curve)
    rets = series.pct_change().dropna()
    wins = [r for r in period_rets if r > 0]
    losses = [r for r in period_rets if r <= 0]
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("inf")
    sharpe = (rets.mean() / rets.std() * np.sqrt(24 * 365)) if len(rets) > 1 and rets.std() > 0 else 0.0
    dd = ((series / series.cummax()) - 1).min() * 100.0
    return {"ret": (series.iloc[-1] - 1.0) * 100.0, "pf": pf,
            "wr": (len(wins) / len(period_rets) * 100.0) if period_rets else 0.0,
            "n": len(period_rets), "dd": dd, "sharpe": sharpe, "n_bars": n_bars}


def _emit(sid: str, win: dict, run_window, params: dict):
    rows = []
    for label, (w0, w1) in win.items():
        m = run_window(w0, w1)
        rows.append({"id": f"{sid}_{label}", "name": f"{sid} [{label}]",
                     "ret_pct": float(m["ret"]), "pf": float(m["pf"]),
                     "wr_pct": float(m["wr"]), "n": int(m["n"]),
                     "dd_pct": float(m["dd"]), "sharpe": float(m["sharpe"])})
    full = next(r for r in rows if r["id"].endswith("_FULL"))
    oos = next((r for r in rows if r["id"].endswith("_OOS")), None)
    metrics = {"ret_pct": full["ret_pct"], "pf": full["pf"], "n": full["n"],
               "dd_pct": full["dd_pct"], "sharpe": full["sharpe"],
               "windows": {r["id"]: {k: r[k] for k in ("ret_pct", "pf", "n", "dd_pct", "sharpe")}
                           for r in rows}}
    return metrics, rows
