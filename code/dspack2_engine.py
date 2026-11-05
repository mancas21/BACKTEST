#!/usr/bin/env python
"""dspack2 -- adapter runner for the DeepSeek SECOND pack
(`deepseek_python_20261022_848478.py`, shipped UNMODIFIED as
`code/deepseek_pack2.py` sha256 bba9c6d61b57b370...; this runner IMPORTS it --
no byte edits -- and declares what the pack file does not).

Like pack 1 (`code/deepseek_pack.py`, run by `dspack_engine.py`), the file is
FOUR pure signal functions only: no imports, no costs, no fills, no numbers.
The DECLARED contract below is identical to dspack_engine's -- because this
engine REUSES dspack_engine's accounting verbatim: core_factors /
core_factors_portfolio / segment_trades / segment_periods / scoring all come
from `import dspack_engine` (a sibling file), never copied. One accounting,
two packs on top of it; any change to the shared accounting changes this
adapter's run_ids because the harness hashes both engine files into
`engine_sha256`.

STRATS (author call paths, verbatim defaults):
  ds6 bb_reversion    strat_bb_reversion(df)   -- z=(close-SMA20)/SD20;
      long on (z<-2 & ADX<20), short on (z>+2 & ADX<20); the exit loop only
      ever WRITES 0, so a position exists ONLY on trigger bars (the ds2/
      donchian stateless pattern -- audited below, not assumed).
      Author-side note kept as-is: "ADX" here is the pack's own simplified
      variant (SMA of DI over an SMA of TR), not Wilder's.
  ds7 rsi2            strat_rsi2(df)           -- Connors RSI(2) entry<10
      while close>EMA200, exit RSI>60. Long only. STATEFUL hold loop (the
      only stateful strat of this pack).
  ds8 pairs           strat_pairs(panel)       -- log(log-BTC)-log(ETH)
      spread z over rolling(168); long A on z<-2, short A on z>+2, flatten
      marker at |z|<0.5; leg-B dollar weight = -pos_a * (b/a) (a 1:1 SHARE
      hedge: q_b/b = q_a/a). STATELESS trigger bars; scored with the ds4
      portfolio accounting (period segmentation). Panel keys are the
      author's own "BTC/USDT"/"ETH/USDT" -- the engine pre-aligns BTC and
      ETH onto their intersection BEFORE the call, because the author code
      indexes panel[a].close directly (unlike strat_xs_momentum, it does
      NOT dropna-align internally; unaligned indexes would silently
      broadcast on the union).
  ds9 vwap_reversion  strat_vwap_reversion(df) -- rolling(24) VWAP of
      close*volume; z-score of the deviation; long z<-2, short z>+2, marker
      0. The trailing .ffill(limit=12) is a NO-OP (nothing is NaN -- every
      bar already carries 0.0 or +-1) and the audit proves it.

FILL TIME  the pack functions read data through bar t and return pos(t).
The fill happens at the CLOSE of bar t (the dspack_engine / emaadx
process_orders_on_close convention). Bar t+1 PnL = pos(t) * (close[t+1]/
close[t] - 1). No next-open fills, nothing else.

FEE/TRADE/PERIOD ACCOUNTING, WINDOWS, BENCHMARK, ANNUALIZATION, GATES:
identical to dspack_engine.py's docstring (reused code = reused contract).
  GATES  G1 pf_strict > 1.2   G2 n_trades >= 30  G3 pf_h1 > 1.0 and
         pf_h2 > 1.0   G4 (full only) green years >= 2 of 3
         G5 ret > benchmark on the same span
         G6 conc_net_without_top5_pct > 0
Costs: repo6x5 (6bp taker + 5bp slippage per side) is the scored preset;
zero-cost (the author's own implicit preset) re-runs INSIDE every artifact
as ret_zero_pct / pf_zero / drag_pp -- the verbatim-call-path baseline and
a determinism check in one.

DATA: harness-native 1h klines only (`data/binance_klines_1h/`). The shared
load_csv REFUSES any file whose median bar spacing is not ~60min, so the
pack's own 1h-declared constants (bars_per_year 8760, lookbacks 168/24) keep
their meaning.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

import dspack_engine as E

HERE = os.path.dirname(os.path.abspath(__file__))
STRATS = ("ds6", "ds7", "ds8", "ds9")

PAIR_FILES = {"BTCUSDT": "BTC/USDT", "ETHUSDT": "ETH/USDT"}


def load_author_module():
    """Import the author pack 2 file with np/pd injected before exec.

    The author file imports NOTHING (uses df.* / np.* / pd.* bare) and must
    stay byte-identical on disk; it is hashed into every run_id through the
    adapter's sources list. Same pattern as dspack_engine.load_author_module
    for pack 1 != same function: pack 1's loader points at deepseek_pack.py
    and is NOT reusable for this file.
    """
    import importlib.util
    import sys as _sys
    path = os.path.join(HERE, "deepseek_pack2.py")
    if not os.path.exists(path):
        raise FileNotFoundError(
            "code/deepseek_pack2.py missing -- copy the author pack into "
            "code/ before running (Downloads/ is not durable; SAX lesson)")
    spec = importlib.util.spec_from_file_location("deepseek_pack2", path)
    mod = importlib.util.module_from_spec(spec)
    mod.np = np
    mod.pd = pd
    _sys.modules["deepseek_pack2"] = mod
    spec.loader.exec_module(mod)
    return mod


def positions_single(df: pd.DataFrame, strat: str) -> np.ndarray:
    pack = load_author_module()
    if strat == "ds6":
        w = pack.strat_bb_reversion(df)
    elif strat == "ds7":
        w = pack.strat_rsi2(df)
    elif strat == "ds9":
        w = pack.strat_vwap_reversion(df)
    else:
        raise ValueError(f"unknown per-symbol strat {strat!r}")
    w = np.asarray(w, dtype=float)
    return np.nan_to_num(w, nan=0.0, posinf=0.0, neginf=0.0)


def positions_pairs(dfs: dict) -> np.ndarray:
    """ds8 on a PRE-ALIGNED 2-leg panel; returns the (n, 2) weight matrix.

    The pack returns dict[author-key -> Series]; column order is fixed to
    ("BTC/USDT", "ETH/USDT") so `closes` and `W` stay row-aligned and the
    artifact is deterministic.
    """
    pack = load_author_module()
    src = {PAIR_FILES[s]: dfs[s] for s in ("BTCUSDT", "ETHUSDT")}
    pos = pack.strat_pairs(src)          # verbatim author defaults
    cols = sorted(pos.keys())
    if cols != sorted(PAIR_FILES.values()):
        raise ValueError(f"strat_pairs returned legs {cols}, expected "
                         f"{sorted(PAIR_FILES.values())}")
    W = pd.DataFrame({k: pos[k] for k in ("BTC/USDT", "ETH/USDT")})
    return np.nan_to_num(W.to_numpy(dtype=float),
                         nan=0.0, posinf=0.0, neginf=0.0)


def run_suite(paths: list, params: dict) -> dict:
    strat = params.get("strat")
    window = params.get("window", "full")
    cost_name = params.get("costs", "repo6x5")
    if strat not in STRATS:
        raise ValueError(f"unknown strat {strat!r}; expected {list(STRATS)}")
    if window not in ("full", "last6mo"):
        raise ValueError(f"unknown window {window!r}")
    if cost_name not in E.COST_PRESETS:
        raise ValueError(f"unknown cost preset {cost_name!r}; "
                         f"expected {sorted(E.COST_PRESETS)}")
    costs = E.COST_PRESETS[cost_name]
    c = float(costs["taker_fee"] + costs["slippage"])

    if strat == "ds8":
        if len(paths) != 2:
            raise ValueError("ds8 takes exactly two files: BTCUSDT and ETHUSDT")
        heads = sorted(E._head(p) for p in paths)
        if heads != sorted(PAIR_FILES):
            raise ValueError("ds8 needs the canonical BTC/ETH 1h files "
                             f"(got {heads})")
        dfs = {E._head(p): E.load_csv(p) for p in paths}
        # align the legs FIRST (the author code does not do it), then window
        closes_full = E.aligned_closes(dfs)
        n_full = len(closes_full)
        if window == "last6mo":
            need = E.WARMUP_BARS + E.SCORE_BARS
            if n_full < need:
                raise ValueError(f"pairs intersection has {n_full} bars; "
                                 f"last6mo needs {need}")
            keep = closes_full.index[-need:]
        else:
            keep = closes_full.index
        src = {h: dfs[h].reindex(keep).dropna(subset=["close"]) for h in dfs}
        closes = E.aligned_closes(src)
        if len(closes) != len(keep):
            raise AssertionError(f"pair alignment lost bars: {len(closes)} "
                                 f"vs {len(keep)}")
        cl = closes.to_numpy()
        n, idx = len(cl), closes.index
        sf = E.WARMUP_BARS if window == "last6mo" else 0
        W = positions_pairs(src)
        if W.shape != (n, 2):
            raise AssertionError(
                f"ds8 weights {W.shape} != aligned closes {(n, 2)}")
        bench_ret = ((float(np.prod(1.0 + ((cl[1:] / cl[:-1] - 1.0).mean(axis=1))))
                      - 1.0) * 100.0) if n > sf + 1 else float("nan")
        acct = E.run_portfolio_account(W, cl, c)
        acct0 = E.run_portfolio_account(W, cl, 0.0)
        row = E._score_periods(acct["seg"], acct["factors"]["lv"], idx, sf, n,
                               bench_ret)
        zrow = E._score_periods(acct0["seg"], acct0["factors"]["lv"], idx, sf,
                                n, bench_ret)
        pair = "PAIRS_BTC_ETH"
    else:
        if len(paths) != 1:
            raise ValueError(f"{strat} takes exactly one symbol file")
        sym = E._head(paths[0])
        df = E.load_csv(paths[0])
        if window == "last6mo":
            need = E.WARMUP_BARS + E.SCORE_BARS
            if len(df) < need:
                raise ValueError(f"{sym} has only {len(df)} bars; last6mo "
                                 f"needs {need}")
            df = df.iloc[-need:]
        w = positions_single(df, strat)
        close = df["close"].to_numpy()
        n = len(df)
        idx = df.index
        sf = E.WARMUP_BARS if window == "last6mo" else 0
        bench_ret = ((float(close[-1] / close[sf - 1] - 1.0) * 100.0)
                     if sf >= 1 else
                     (float(close[-1] / close[0] - 1.0) * 100.0))
        acct = E.run_symbol_account(w, close, c)
        acct0 = E.run_symbol_account(w, close, 0.0)
        row = E._score_trades(acct["seg"], acct["factors"]["lv"], idx, sf, n,
                              bench_ret)
        zrow = E._score_trades(acct0["seg"], acct0["factors"]["lv"], idx, sf,
                               n, bench_ret)
        pair = sym

    row["ret_zero_pct"] = zrow["ret_pct"]
    row["pf_zero"] = zrow["pf_strict"]
    row["drag_pp"] = ((zrow["ret_pct"] - row["ret_pct"])
                      if row["ret_pct"] is not None else None)
    E._gates(row, window)   # shared G1-G6 gate booleans on the row, exactly
    # like dspack_engine.run_suite (the report/guard read gates_pass_all)

    spacing_ns = E._spacing(idx)
    if spacing_ns:
        bpy_meas = 365.25 * 24.0 * 3600.0 / (spacing_ns / 1e9)
    else:
        bpy_meas = None

    metrics = {
        "strat": strat, "window": window, "costs": cost_name,
        "pair": pair,
        "score_from": int(sf),
        "warmup_bars": int(sf) if window == "last6mo" else 0,
        "engine_slice_bars": int(n),
        "scored_bars": int(n - sf),
        "scored_start": str(idx[sf]), "scored_end": str(idx[-1]),
        "bars_per_year_measured": bpy_meas,
        "bench_ret_pct": bench_ret,
        "aligned_bars_full": int(n_full) if strat == "ds8" else int(n),
    }
    return {"metrics": metrics, "tables": [{k: E._clean(v) for k, v in row.items()}]}
