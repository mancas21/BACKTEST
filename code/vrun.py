#!/usr/bin/env python
"""vrun.py -- the artifact harness.

RECONSTRUCTED 2026-10-17. The original harness bytes were lost: the file occupying
this path was a different, non-parsing program (preserved as
`code/attic/vrun_broken_2026-10-16.py`, sha256 65BC299B...). This replacement was
derived from the 186 artifacts on disk, not guessed:

  * run_id = sha256(json.dumps(core, sort_keys=True, separators=(",", ":")))[:16]
    verified against all 186 stored run_ids.
  * engine_sha256 = sha256 of the engine source files' BYTES CONCATENATED in
    filename-sorted order (single file -> that file's own sha256). Verified
    against every engine file still on disk.
  * core = {strategy, params, inputs:[[path, sha256, bars]], engine_sha256,
    engine_version}. harness_sha256 is recorded in provenance but is NOT part of
    core, so fixing the harness does not invalidate an artifact. That is the
    original design and it is why this reconstruction can restore verification.

WHY THE ENGINE IS WHAT IT IS
    `inputs` hash the DATA and `engine_sha256` hashes the ENGINE. If either
    changes the run_id changes and the old artifact can no longer verify. That is
    the whole point: a number with no reproducible artifact behind it is not a
    result (AGENTS.md REGLA 0).

Commands
    run     --strategy cbot --tf 1m --symbol BTCUSDT [--set k=v]
    render  <run_id>
    verify  <run_id>         0 OK | 2 REFUSED (drift) | 3 STALE (data extended)
    matrix  --strategy cbot [--tf 1h,15m]
    pmatrix --strategy cbot [--tf 1h,15m] [--workers N]   parallel matrix
    pverify --strategy cbot | --ids id1,id2 [--workers N] [--quiet]
    guard   --report report.md
    show
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import glob
import os
import re
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CODE = os.path.join(ROOT, "code")
RUNS = os.path.join(ROOT, "results", "runs")
SCHEMA = "bt-artifact/1"

# harness-native (non-taker) data directories, by timeframe
TF_DIR = {
    "1h":  (os.path.join(DATA, "binance_klines_1h"),  "1h"),
    "15m": (os.path.join(DATA, "binance_klines_15m"), "15m"),
    "5m":  (os.path.join(DATA, "binance_klines"),     "5m"),
    "1m":  (os.path.join(DATA, "binance_klines_1m"),  "1m"),
}
# taker-field data (Binance kline field 9). Only cbot's S05/S06 need it.
TF_TAKER = {
    "1h":  (os.path.join(DATA, "binance_klines_1h_taker"),  "1h"),
    "15m": (os.path.join(DATA, "binance_klines_15m_taker"), "15m"),
    "5m":  (os.path.join(DATA, "binance_klines_5m_taker"),  "5m"),
    "1m":  (os.path.join(DATA, "binance_klines_1m_taker"),  "1m"),
}

MIN_TRADE_FLAG = 30

# The SAX v3 engine is GONE from disk. Its 49 artifacts are permanently
# unverifiable; the adapter exists only so the failure is explicit rather than a
# "no such strategy" error that looks like a typo.
SAX_ENGINE = os.path.join(os.path.expanduser("~"), "Downloads", "sax_engine-claude.py")
SAX_ENGINE_SHA = "e991efc36515ade5f54f70a0bd6514955c47dd520a10f7a1ba02eead29a2e7b3"


# ══════════════════════════════════════════════ hashing / loading
def _sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_engine(paths: list) -> str:
    """sha256 over the engine files' bytes concatenated in filename-sorted order.

    Recovered from the artifacts: for every engine still on disk this reproduces
    the recorded engine_sha256 exactly (single-file engines reduce to that file's
    own sha256). Sorting is on the BASENAME, which is also what provenance
    .engine_files records.
    """
    ordered = sorted(paths, key=lambda p: os.path.basename(p))
    h = hashlib.sha256()
    for p in ordered:
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()


_MODCACHE = {}


def _load_module(path: str, name: str):
    """Import a source file by path, swallowing module-level prints.

    ffs_engine.py and ffs_engine2.py both execute a demo loop at import time
    (they print a table and read 1m CSVs). That is the engines' own code and it
    is not ours to edit, so the harness imports them once and discards the text.
    """
    if name in _MODCACHE:
        return _MODCACHE[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            spec.loader.exec_module(mod)
    finally:
        _MODCACHE[name] = mod
    return mod


def _load_fresh(path: str, name: str):
    """An UNCACHED module object, for runs that mutate module-level config.

    _load_module caches by name, so setting EQUITY_PCT on its result would leak
    into every later run in the same process (matrix mode, verify after a matrix).
    Loading a fresh instance keeps the engine FILE byte-identical while making a
    sizing override local to one artifact.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        spec.loader.exec_module(mod)
    return mod


def _read_input(p: str) -> dict:
    """Describe one data file the way `inputs` records it."""
    if p.lower().endswith(".parquet"):
        # recorder tape segments (bookTicker/depth/...): arrow table, ms epoch
        import pyarrow.parquet as pq
        import pyarrow.compute as pc
        tbl = pq.read_table(p)
        col = None
        for c in ("recv_ts", "E", "T", "t_open"):
            if c in tbl.column_names:
                col = c
                break
        if col is None:
            raise ValueError(f"{os.path.basename(p)}: no ms-epoch time column in {tbl.column_names}")
        mn = pc.min(tbl.column(col)).as_py()
        mx = pc.max(tbl.column(col)).as_py()
        return {"path": os.path.abspath(p), "sha256": _sha256_file(p), "bars": tbl.num_rows,
                "start": str(pd.to_datetime(mn, unit="ms", utc=True)),
                "end": str(pd.to_datetime(mx, unit="ms", utc=True))}
    if p.lower().endswith(".json"):
        # binance funding history: a JSON list of {t: ms, r: rate}
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        recs = [x for x in data if isinstance(x, dict) and "t" in x]
        if not recs:
            raise ValueError(f"{os.path.basename(p)}: expected a JSON list of records with a 't' key")
        times = pd.to_datetime([x["t"] for x in recs], unit="ms", utc=True)
        return {"path": os.path.abspath(p), "sha256": _sha256_file(p), "bars": len(recs),
                "start": str(times[0]), "end": str(times[-1])}
    df = pd.read_csv(p)
    df.columns = [str(c).strip() for c in df.columns]
    tcol = None
    for c in df.columns:
        lc = c.lower()
        if lc in ("open_ts", "open_time", "timestamp", "time", "datetime", "date",
                  "transact_time"):
            tcol = c
            break
    if tcol is None:
        raise ValueError(f"{os.path.basename(p)}: no time column in {list(df.columns)}")
    ts = df[tcol]
    if pd.api.types.is_numeric_dtype(ts):
        time = pd.to_datetime(ts, unit="ms", utc=True)
    else:
        time = pd.to_datetime(ts, utc=True)
    res = {"path": os.path.abspath(p), "sha256": _sha256_file(p), "bars": int(len(df)),
           "start": str(time.iloc[0]), "end": str(time.iloc[-1])}
    if len(time) > 2:
        d_sec = time.diff().dropna().dt.total_seconds()
        base_s = float(d_sec.median())
        if base_s > 0:
            gaps = d_sec[d_sec > 1.5 * base_s]
            max_gap = float(round(gaps.max() / base_s, 1)) if len(gaps) > 0 else 1.0
            missing = int(round(((gaps / base_s) - 1.0).clip(lower=0).sum())) if len(gaps) > 0 else 0
            res["max_gap_bars"] = max_gap
            res["missing_bars"] = missing
            res["gap_breach"] = bool(max_gap > 24.0)
    return res


# ══════════════════════════════════════════════ dspack (DeepSeek 5-pack)
def run_dspack(paths, params):
    """The attached DeepSeek five-strategy pack, ported through
    code/deepseek_pack.py -- that file is the ATTACHMENT copied
    byte-identical (source of record); the engine imports it and injects
    numpy/pandas, nothing else. Porting conventions are declared in the
    engine's docstring (fill at signal-bar close, whole-order fee on the
    bar where |dw|>0 with the closing trade paying reversal fees, ds4 under
    period accounting with a rebalanced equal-weight benchmark).

    Pack quirks ported faithfully (audit-pinned, code/_dspack_audit.py):
      * ds2 (donchian) and ds5 (breakout+volume) are STATELESS. ds2 rewrites
        pos from 0 every bar; ds5's ffill(limit=24) is a DEAD NO-OP because
        pos never contains NaN -- the author's 24-bar hold never happens.
      * ds3 flips to -1 (short) when its memory ages out, not flat.
      * ds1 carries a dead .clip(0, 2) (its final .clip(-1, 1) saturates).
      * ds4 samples xs weights every 24 bars and ffills between.
    Costs: 'author' = 0 fee/0 slip (the pack file declares none; doubles as
    the zero-cost determinism control); 'repo6x5' = 6 bps fee + 5 bps
    slippage per side. drag_pp = zero-cost ret - costed ret, measured
    in-artifact by re-scoring the same book through the 0-cost account.
    ds4 needs all 13 canonical 1h files (symbol PORTFOLIO).
    """
    eng = _load_module(os.path.join(CODE, "dspack_engine.py"), "dspack_engine")
    p = dict(params)
    tf = p.pop("tf", None)
    if tf != "1h":
        raise ValueError(f"dspack supports 1h only (got tf={tf!r})")
    out = eng.run_suite(paths, p)
    row = out["tables"][0] if out["tables"] else {}
    metrics = dict(out["metrics"])
    metrics.update({
        "return_pct": row.get("ret_pct"),
        "profit_factor": row.get("pf_strict"),
        "n_trades": row.get("n_trades"),
        "win_rate": row.get("win_rate_pct"),
        "max_dd_pct": row.get("max_dd_pct"),
    })
    prov = {"adapter": "dspack", "engine_version": "dspack-1",
            "strat": row.get("strat"), "window": row.get("window"),
            "costs": row.get("costs"),
            "gates_pass_all": bool(row.get("gates_pass_all"))}
    return metrics, prov, out["tables"]


def run_dspack2(paths, params):
    """DeepSeek SECOND pack (strats 6-9) — attachment
    `deepseek_python_20261022_848478.py` copied BYTE-IDENTICAL to
    code/deepseek_pack2.py (sha256 bba9c6d61b57b370...; source of record).
    Engine code/dspack2_engine.py IMPORTS dspack_engine's accounting
    verbatim (one copy, no duplicates; both engine files plus the author
    file are hashed into every run_id via this adapter's sources), and was
    known-answer audited BEFORE any real-data run: 36 cases ALL PASS
    (results/dspack2_audit_known_answers.txt).

    Pack quirks ported faithfully (audit-pinned):
      * ds6 (BB-z reversion) and ds9 (VWAP-deviation reversion) are
        STATELESS: positions exist ONLY on trigger bars (ds6's exit loop
        only ever writes 0; ds9's ffill(limit=12) is a dead no-op because
        nothing is NaN).
      * ds7 (RSI-2 Connors) is STATEFUL long-only (RSI(2)<10 & close >
        EMA200 in, RSI>60 out) — the only holding strat of this pack.
      * ds8 is the BTC/ETH log-spread pairs book, scored with the ds4
        PERIOD accounting on a pre-aligned panel (symbol PAIRS_BTC_ETH);
        leg-B dollar weight = -pos_a * (b/a) — a 1:1 SHARE hedge.
    Costs: 'repo6x5' (6 bps fee + 5 bps slippage per side) scored; the
    author's implicit 0-cost baseline re-runs in-artifact as ret_zero_pct
    / pf_zero / drag_pp. ds6/ds7/ds9 also carry the shared G1-G6 gate
    booleans (gates_pass_all).
    """
    eng = _load_module(os.path.join(CODE, "dspack2_engine.py"),
                       "dspack2_engine")
    p = dict(params)
    tf = p.pop("tf", None)
    if tf != "1h":
        raise ValueError(f"dspack2 supports 1h only (got tf={tf!r})")
    out = eng.run_suite(paths, p)
    row = out["tables"][0] if out["tables"] else {}
    metrics = dict(out["metrics"])
    metrics.update({
        "return_pct": row.get("ret_pct"),
        "profit_factor": row.get("pf_strict"),
        "n_trades": row.get("n_trades"),
        "win_rate": row.get("win_rate_pct"),
        "max_dd_pct": row.get("max_dd_pct"),
    })
    prov = {"adapter": "dspack2", "engine_version": "dspack2-1",
            "strat": row.get("strat"), "window": row.get("window"),
            "costs": row.get("costs"),
            "gates_pass_all": bool(row.get("gates_pass_all"))}
    return metrics, prov, out["tables"]


def run_hmaaoadx(paths, params):
    """Fingrad HMA·AO·ADX (Pine v6 attachment) via the port engine
    code/hmaaoadx_engine.py, which imports the known-answer audited Pine
    primitives (rma/atr_pine/dmi_pine/cross_over/cross_under) from
    code/emaadx_engine.py BY IDENTITY and the dspack scorer verbatim, and
    was itself audited BEFORE any real-data run: 42 cases ALL PASS
    (results/hmaaoadx_audit_known_answers.txt).

    Signals evaluate on bar close, orders fill at the NEXT bar's open
    (process_orders_on_close=false), the ATR bracket arms from the fill
    price, stop-first on spanning bars, gap rule = fill at the open,
    daily-loss breaker 3% of day-start equity (UTC day change resets).
    Costs: repo6x5 (6 bps fee + 5 bps slippage per side) scored; a
    zero-cost control pass re-runs in-artifact (ret_zero_pct / pf_zero /
    drag_pp); 'author' (0.05% + 0.01%, the input mirror) is available.
    Strategy geometry = the Pine defaults only -- `window` and `costs`
    are the CLI parameters (PINE dict; the audit pins the rest).
    """
    eng = _load_module(os.path.join(CODE, "hmaaoadx_engine.py"),
                       "hmaaoadx_engine")
    p = dict(params)
    tf = p.pop("tf", None)
    if tf != "1h":
        raise ValueError(f"hmaaoadx supports 1h only (got tf={tf!r})")
    out = eng.run_suite(paths, p)
    row = out["tables"][0] if out["tables"] else {}
    metrics = dict(out["metrics"])
    metrics.update({
        "return_pct": row.get("ret_pct"),
        "profit_factor": row.get("pf_strict"),
        "n_trades": row.get("n_trades"),
        "win_rate": row.get("win_rate_pct"),
        "max_dd_pct": row.get("max_dd_pct"),
    })
    prov = {"adapter": "hmaaoadx", "engine_version": "hmaaoadx-1",
            "strat": row.get("strat"), "window": row.get("window"),
            "costs": row.get("costs"),
            "gates_pass_all": bool(row.get("gates_pass_all"))}
    return metrics, prov, out["tables"]
def _flag(n: int) -> str:
    return "OK" if n >= MIN_TRADE_FLAG else "INSUFFICIENT_SAMPLE"


def run_cbpack(paths, params):
    """strategy_pack.py (the "QUANT CRYPTO BOT 10" pack) through its own evaluate_all.

    The engine is the pack's own code, copied byte-identical into
    code/cbpack_engine.py so the artifact stays reproducible if the attached file
    in Downloads is ever moved or deleted -- exactly what happened to the SAX v3
    engine, which is why that whole engine is now unverifiable.

    Provenance notes that matter for reading the numbers:
      * `prepare()` keeps taker_buy_base as `taker_buy`, so flow is TRUE taker
        flow, not the candle-colour proxy. The pack reports flow_source itself.
      * funding is attached when data/binance_funding/<SYM>_funding.json exists
        (every symbol except JUPUSDT). The file's bytes are hashed into `inputs`.
      * open interest is NOT attached: Binance serves only ~20 days of OI
        history, so S08 is skipped, never approximated.
    """
    pack = _load_module(os.path.join(CODE, "cbpack_engine.py"), "cbpack_engine")
    p = dict(params)
    _tf = p.pop("tf")
    fee = float(p.pop("fee_bps", 5.0))   # repo 2026-10-25: 5+0.5 = 11 bps RT
    slip = float(p.pop("slippage_bps", 0.5))  # medido en libro vivo
    slice_from = p.pop("slice_from", None)
    slice_to = p.pop("slice_to", None)
    use_funding = bool(p.pop("funding", True))
    mode = str(p.pop("mode", "full")).lower()
    wf_ids = p.pop("ids", None)
    wf_train = p.pop("train_bars", None)
    wf_test = p.pop("test_bars", None)
    wf_min_trades = int(p.pop("min_trades", 20))
    wf_objective = str(p.pop("objective", "sharpe_annualised"))
    if mode not in ("full", "wf"):
        raise ValueError(f"unknown cbpack mode: {mode!r} (use 'full' or 'wf')")
    if mode == "wf" and not (wf_train and wf_test):
        raise ValueError("mode=wf needs train_bars and test_bars")
    if p:
        raise ValueError(f"unknown cbpack params: {sorted(p)}")

    klines, funding_path = paths[0], (paths[1] if len(paths) > 1 else None)
    raw = pd.read_csv(klines)
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    raw = raw.rename(columns={"open_ts": "open_time"})     # the pack looks for open_time
    raw["open_time"] = pd.to_datetime(raw["open_time"], unit="ms", utc=True)
    df = pack.prepare(raw.set_index("open_time"))
    if slice_from:
        df = df[df.index >= pd.Timestamp(slice_from, tz="UTC")]
    if slice_to:
        df = df[df.index < pd.Timestamp(slice_to, tz="UTC")]
    if len(df) < 500:
        raise ValueError(f"only {len(df)} bars after slicing -- not enough to test")

    if use_funding and funding_path:
        recs = json.load(open(funding_path, encoding="utf-8"))
        idx = pd.DatetimeIndex(pd.to_datetime([x["t"] for x in recs], unit="ms", utc=True))
        # pandas >= 2 makes merge_asof reject mixed datetime resolutions, and
        # `df.index + Timedelta` inside the pack upcasts ms -> us. The pack's own
        # attach_funding therefore raises on pandas 3.x for an ms-resolution
        # funding series. Align the UNIT here (same instants, no semantic change)
        # rather than editing the pack's code.
        _unit = getattr(df.index + pd.Timedelta(seconds=60), "unit", None)
        if _unit is not None and hasattr(idx, "as_unit"):
            idx = idx.as_unit(_unit)
        s = pd.Series([float(x["r"]) for x in recs], index=idx)
        s = s[~s.index.duplicated(keep="last")].sort_index()
        df = pack.attach_funding(df, s)

    cfg = pack.BacktestConfig(fee_bps=fee, slippage_bps=slip)

    def _nat(v):
        if v is None:
            return None
        if isinstance(v, (bool, np.bool_)):
            return bool(v)
        if isinstance(v, str):
            return v
        if isinstance(v, (int, np.integer)):
            return int(v)
        return float(v)

    # ── walk-forward mode ────────────────────────────────────────────────
    # The pack ships its own walk_forward: the grid is re-selected on every train
    # window and traded untouched on the next test window, and because signals are
    # causal it computes each combo's signals once over the full series (no leak).
    # Exposed as an adapter mode so the OOS numbers land in a verifiable artifact
    # instead of in a console log -- REGLA 0 applies to out-of-sample too.
    if mode == "wf":
        ids = ([s.strip() for s in wf_ids.split(",") if s.strip()]
               if isinstance(wf_ids, str) else (wf_ids or list(pack.STRATEGIES)))
        tables = []
        for sid in ids:
            spec = pack.STRATEGIES[sid]
            res = pack.walk_forward(df, sid, cfg, int(wf_train), int(wf_test),
                                    objective=wf_objective, min_trades=wf_min_trades)
            folds, summ = res["folds"], res["summary"]
            tables.append({"kind": "summary", "id": sid, "name": spec.name,
                           "folds": int(summ["folds"]),
                           "oos_net_%": float(summ["oos_compounded_net_%"]),
                           "folds_profitable": int(summ["folds_profitable"]),
                           "mean_train_net_%": float(summ["mean_train_net_%"]),
                           "mean_test_net_%": float(summ["mean_test_net_%"]),
                           "grid_combos": int(np.prod([len(v) for v in spec.grid.values()])),
                           "train_bars": int(wf_train), "test_bars": int(wf_test),
                           "min_trades": int(wf_min_trades), "objective": wf_objective})
            for rec in folds.to_dict(orient="records"):
                prm = rec.get("params")
                tables.append({"kind": "fold", "id": sid, "fold": int(rec["fold"]),
                               "params": (",".join(f"{k}={v}" for k, v in sorted(prm.items()))
                                          if isinstance(prm, dict) else ""),
                               "train_obj": rec.get("train_obj", float("nan")),
                               "train_net_%": rec.get("train_net_%", float("nan")),
                               "test_net_%": rec.get("test_net_%", float("nan")),
                               "test_buy_hold_%": rec.get("test_buy_hold_%", float("nan")),
                               "test_trades": rec.get("test_trades", float("nan")),
                               "test_PF": rec.get("test_PF", float("nan"))})
        tables = [{k: _nat(v) for k, v in row.items()} for row in tables]
        summaries = [r for r in tables if r["kind"] == "summary"]
        frows = [r for r in tables if r["kind"] == "fold"]
        oos_bh = float(np.mean([r["test_buy_hold_%"] for r in frows
                                if np.isfinite(r["test_buy_hold_%"])])) if frows else float("nan")
        best_oos, best_oos_id = max(((r["oos_net_%"], r["id"]) for r in summaries),
                                    default=(float("nan"), None))
        metrics = {
            "bars": int(len(df)), "n_strategies": len(summaries),
            "train_bars": int(wf_train), "test_bars": int(wf_test),
            "min_trades": int(wf_min_trades), "objective": wf_objective,
            "total_folds": sum(r["folds"] for r in summaries),
            "sum_folds_profitable": sum(r["folds_profitable"] for r in summaries),
            "cost_bp_roundtrip": 2.0 * (fee + slip),
            "fee_bps_per_side": fee, "slippage_bps_per_side": slip,
            "funding_attached": bool(use_funding and funding_path),
            "oos_bh_mean_pct": oos_bh,
            "best_oos_net_pct": float(best_oos), "best_oos_id": best_oos_id,
            "n_oos_positive": sum(1 for r in summaries
                                  if np.isfinite(r["oos_net_%"]) and r["oos_net_%"] > 0),
        }
        prov = {"adapter": "cbpack", "engine_version": "cbpack-1", "mode": "wf",
                "source_file": "Downloads/strategy_pack.py", "flow": "taker_buy_base",
                "costs": {"fee_bps": fee, "slippage_bps": slip}}
        return metrics, prov, tables

    tab = pack.evaluate_all(df, cfg)
    tables = [{k: _nat(v) for k, v in row.items()} for row in tab.to_dict(orient="records")]
    ok = [r for r in tables if r.get("status") == "ok"]
    bh = float(ok[0]["buy_hold_%"]) if ok else float("nan")

    def _best(key):
        vals = [(r[key], r["id"]) for r in ok
                if isinstance(r.get(key), float) and np.isfinite(r[key])]
        return max(vals) if vals else (float("nan"), None)

    best_net, best_net_id = _best("net_%")
    best_pf, best_pf_id = _best("PF")
    metrics = {
        "n_strategies": len(tables), "n_ok": len(ok), "n_skipped": len(tables) - len(ok),
        "bars": int(len(df)), "bh_return_pct": bh,
        "cost_bp_roundtrip": 2.0 * (fee + slip),
        "fee_bps_per_side": fee, "slippage_bps_per_side": slip,
        "best_net_pct": float(best_net), "best_net_id": best_net_id,
        "best_pf": float(best_pf), "best_pf_id": best_pf_id,
        "n_net_positive": sum(1 for r in ok if r["net_%"] > 0),
        "n_pf_gt_1p2_n30": sum(1 for r in ok if r["PF"] > 1.2 and r["trades"] >= 30),
        "funding_attached": bool(use_funding and funding_path),
    }
    prov = {"adapter": "cbpack", "engine_version": "cbpack-1", "mode": "full",
            "source_file": "Downloads/strategy_pack.py", "flow": "taker_buy_base",
            "costs": {"fee_bps": fee, "slippage_bps": slip}}
    return metrics, prov, tables


def run_cbpackf(paths, params):
    """strategy_pack.py through the FUNDING-AWARE fork (code/cbpack_funding_engine.py).

    Identical to run_cbpack in every respect except two, both deliberate:

      1. FUNDING IS CHARGED. The original pack attaches a funding_rate column but
         never debits it from PnL -- its own docstring says "No funding payments".
         A Binance USDT-M perpetual charges funding every 8h on the open notional.
         A `funding_attached: true` flag in the original artifact's provenance
         means the COLUMN was attached, not that the COST was charged.

      2. CONCENTRATION DIAGNOSTICS. Every strategy row also carries the share of
         total PnL held by its best 5 trades, and the return it would have made
         without them. A strategy whose best 5 trades exceed 100% of total PnL is
         a handful of lucky positions, not an edge.

    The engine file is a separate file, so the run_id changes automatically: an
    artifact from this adapter can never be confused with a cbpack-1 artifact.
    """
    pack = _load_module(os.path.join(CODE, "cbpack_funding_engine.py"), "cbpack_funding_engine")
    p = dict(params)
    _tf = p.pop("tf")
    fee = float(p.pop("fee_bps", 5.0))   # repo 2026-10-25: 5+0.5 = 11 bps RT
    slip = float(p.pop("slippage_bps", 0.5))  # medido en libro vivo
    slice_from = p.pop("slice_from", None)
    slice_to = p.pop("slice_to", None)
    use_funding = bool(p.pop("funding", True))
    mode = str(p.pop("mode", "full")).lower()
    wf_ids = p.pop("ids", None)
    wf_train = p.pop("train_bars", None)
    wf_test = p.pop("test_bars", None)
    wf_min_trades = int(p.pop("min_trades", 20))
    wf_objective = str(p.pop("objective", "sharpe_annualised"))
    if mode not in ("full", "wf"):
        raise ValueError(f"unknown cbpackf mode: {mode!r} (use 'full' or 'wf')")
    if mode == "wf" and not (wf_train and wf_test):
        raise ValueError("mode=wf needs train_bars and test_bars")
    if p:
        raise ValueError(f"unknown cbpackf params: {sorted(p)}")

    klines, funding_path = paths[0], (paths[1] if len(paths) > 1 else None)
    raw = pd.read_csv(klines)
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    raw = raw.rename(columns={"open_ts": "open_time"})
    raw["open_time"] = pd.to_datetime(raw["open_time"], unit="ms", utc=True)
    df = pack.prepare(raw.set_index("open_time"))
    if slice_from:
        df = df[df.index >= pd.Timestamp(slice_from, tz="UTC")]
    if slice_to:
        df = df[df.index < pd.Timestamp(slice_to, tz="UTC")]
    if len(df) < 500:
        raise ValueError(f"only {len(df)} bars after slicing -- not enough to test")

    n_settlements = 0
    if use_funding and funding_path:
        recs = json.load(open(funding_path, encoding="utf-8"))
        idx = pd.DatetimeIndex(pd.to_datetime([x["t"] for x in recs], unit="ms", utc=True))
        _unit = getattr(df.index + pd.Timedelta(seconds=60), "unit", None)
        if _unit is not None and hasattr(idx, "as_unit"):
            idx = idx.as_unit(_unit)
        s = pd.Series([float(x["r"]) for x in recs], index=idx)
        s = s[~s.index.duplicated(keep="last")].sort_index()
        # the pack's own carry-forward column (what S07's z-score reads) ...
        df = pack.attach_funding(df, s)
        # ... PLUS the billing schedule: which bars actually carry a settlement
        df = pack.attach_funding_events(df, s)
        n_settlements = int((df["funding_event_rate"] != 0).sum())

    cfg = pack.BacktestConfig(fee_bps=fee, slippage_bps=slip)

    def _nat(v):
        if v is None:
            return None
        if isinstance(v, (bool, np.bool_)):
            return bool(v)
        if isinstance(v, str):
            return v
        if isinstance(v, (int, np.integer)):
            return int(v)
        return float(v)

    if mode == "wf":
        ids = ([s.strip() for s in wf_ids.split(",") if s.strip()]
               if isinstance(wf_ids, str) else (wf_ids or list(pack.STRATEGIES)))
        tables = []
        for sid in ids:
            spec = pack.STRATEGIES[sid]
            res = pack.walk_forward(df, sid, cfg, int(wf_train), int(wf_test),
                                    objective=wf_objective, min_trades=wf_min_trades)
            folds, summ = res["folds"], res["summary"]
            tables.append({"kind": "summary", "id": sid, "name": spec.name,
                           "folds": int(summ["folds"]),
                           "oos_net_%": float(summ["oos_compounded_net_%"]),
                           "folds_profitable": int(summ["folds_profitable"]),
                           "mean_train_net_%": float(summ["mean_train_net_%"]),
                           "mean_test_net_%": float(summ["mean_test_net_%"]),
                           "grid_combos": int(np.prod([len(v) for v in spec.grid.values()])),
                           "train_bars": int(wf_train), "test_bars": int(wf_test),
                           "min_trades": int(wf_min_trades), "objective": wf_objective})
            for rec in folds.to_dict(orient="records"):
                prm = rec.get("params")
                tables.append({"kind": "fold", "id": sid, "fold": int(rec["fold"]),
                               "params": (",".join(f"{k}={v}" for k, v in sorted(prm.items()))
                                          if isinstance(prm, dict) else ""),
                               "train_obj": rec.get("train_obj", float("nan")),
                               "train_net_%": rec.get("train_net_%", float("nan")),
                               "test_net_%": rec.get("test_net_%", float("nan")),
                               "test_buy_hold_%": rec.get("test_buy_hold_%", float("nan")),
                               "test_trades": rec.get("test_trades", float("nan")),
                               "test_PF": rec.get("test_PF", float("nan"))})
        tables = [{k: _nat(v) for k, v in row.items()} for row in tables]
        summaries = [r for r in tables if r["kind"] == "summary"]
        frows = [r for r in tables if r["kind"] == "fold"]
        oos_bh = float(np.mean([r["test_buy_hold_%"] for r in frows
                                if np.isfinite(r["test_buy_hold_%"])])) if frows else float("nan")
        best_oos, best_oos_id = max(((r["oos_net_%"], r["id"]) for r in summaries),
                                    default=(float("nan"), None))
        metrics = {
            "bars": int(len(df)), "n_strategies": len(summaries),
            "train_bars": int(wf_train), "test_bars": int(wf_test),
            "min_trades": int(wf_min_trades), "objective": wf_objective,
            "total_folds": sum(r["folds"] for r in summaries),
            "sum_folds_profitable": sum(r["folds_profitable"] for r in summaries),
            "cost_bp_roundtrip": 2.0 * (fee + slip),
            "fee_bps_per_side": fee, "slippage_bps_per_side": slip,
            "funding_attached": bool(use_funding and funding_path),
            "funding_charged": True, "n_settlements": n_settlements,
            "oos_bh_mean_pct": oos_bh,
            "best_oos_net_pct": float(best_oos), "best_oos_id": best_oos_id,
            "n_oos_positive": sum(1 for r in summaries
                                  if np.isfinite(r["oos_net_%"]) and r["oos_net_%"] > 0),
        }
        prov = {"adapter": "cbpackf", "engine_version": "cbpack-funding-1", "mode": "wf",
                "source_file": "Downloads/strategy_pack.py", "flow": "taker_buy_base",
                "funding_charged": True,
                "costs": {"fee_bps": fee, "slippage_bps": slip}}
        return metrics, prov, tables

    tab = pack.evaluate_all(df, cfg)
    # The funding drag and the no-funding baseline are MEASUREMENTS, not derived
    # numbers a reader has to subtract: run the original (no-funding) engine on the
    # same data in the same artifact and store both sides. A report can then cite
    # the drag directly, and `guard` can back it.
    # NOTE: to_dict(orient="records") builds fresh dicts on every call, so the
    # records are materialised ONCE and mutated in place.
    orig = _load_module(os.path.join(CODE, "cbpack_engine.py"), "cbpack_engine")
    tab_no = orig.evaluate_all(df, orig.BacktestConfig(fee_bps=fee, slippage_bps=slip))
    no_by_id = {r["id"]: r for r in tab_no.to_dict(orient="records")}
    records = tab.to_dict(orient="records")
    for _r in records:
        _b = no_by_id.get(_r["id"])
        if _b and _r.get("status") == "ok" and _b.get("net_%") is not None:
            _r["net_no_funding_pct"] = _b.get("net_%")
            _r["funding_drag_pp"] = _r["net_%"] - _b["net_%"]
            _r["pf_no_funding"] = _b.get("PF")
        else:
            _r["net_no_funding_pct"] = None
            _r["funding_drag_pp"] = None
            _r["pf_no_funding"] = None
    tables = [{k: _nat(v) for k, v in row.items()} for row in records]
    ok = [r for r in tables if r.get("status") == "ok"]
    bh = float(ok[0]["buy_hold_%"]) if ok else float("nan")

    def _best(key):
        vals = [(r[key], r["id"]) for r in ok
                if isinstance(r.get(key), float) and np.isfinite(r[key])]
        return max(vals) if vals else (float("nan"), None)

    best_net, best_net_id = _best("net_%")
    best_pf, best_pf_id = _best("PF")
    metrics = {
        "n_strategies": len(tables), "n_ok": len(ok), "n_skipped": len(tables) - len(ok),
        "bars": int(len(df)), "bh_return_pct": bh,
        "cost_bp_roundtrip": 2.0 * (fee + slip),
        "fee_bps_per_side": fee, "slippage_bps_per_side": slip,
        "best_net_pct": float(best_net), "best_net_id": best_net_id,
        "best_pf": float(best_pf), "best_pf_id": best_pf_id,
        "n_net_positive": sum(1 for r in ok if r["net_%"] > 0),
        "n_pf_gt_1p2_n30": sum(1 for r in ok if r["PF"] > 1.2 and r["trades"] >= 30),
        "funding_attached": bool(use_funding and funding_path),
        "funding_charged": True, "n_settlements": n_settlements,
        # the two new gates
        "n_conc_pass": sum(1 for r in ok if r.get("conc_passes") is True),
        "n_pass_all_gates": sum(1 for r in ok
                                 if r["net_%"] > 0 and r["PF"] > 1.2 and r["trades"] >= 30
                                 and r.get("conc_passes") is True),
    }
    prov = {"adapter": "cbpackf", "engine_version": "cbpack-funding-1", "mode": "full",
            "source_file": "Downloads/strategy_pack.py", "flow": "taker_buy_base",
            "funding_charged": True,
            "costs": {"fee_bps": fee, "slippage_bps": slip}}
    return metrics, prov, tables


def run_sax(paths, params):
    if not os.path.exists(SAX_ENGINE):
        raise FileNotFoundError(
            f"{SAX_ENGINE} is missing. SAX v3 cannot be re-run, so its artifacts cannot "
            f"verify. Recover the engine or drop the adapter (AGENTS.md, Current kills).")
    raise RuntimeError("SAX v3 engine present but this adapter was not reconstructed; "
                       "refusing to guess at its metrics mapping.")


def run_cvrmd(paths, params):
    C = _load_module(os.path.join(CODE, "cvrmd_backtest.py"), "cvrmd_backtest")
    base = os.path.basename(paths[0])
    sym, tf = base.split("_")[0], base.rsplit("_", 1)[1][:-4]
    eq, tr_, w_, gp, gl, mdd, logs = C.run(sym, C.load(sym, os.path.dirname(paths[0]), tf))
    eq = float(eq)
    metrics = {
        "n_trades": int(tr_), "return_pct": (eq / 10000.0 - 1.0) * 100.0,
        "final_equity": eq, "win_rate": w_ / max(tr_, 1),
        "profit_factor": float(gp / gl) if gl > 0 else (float("inf") if gp > 0 else 0.0),
        "gross_profit": float(gp), "gross_loss": float(gl),
        "max_dd_pct": -float(mdd) * 100.0, "flag": _flag(tr_),
    }
    return metrics, {"adapter": "cvrmd", "engine_version": "cvrmd"}, None


def run_botstrat(paths, params):
    B = _load_module(os.path.join(CODE, "botstrat_backtest.py"), "botstrat_backtest")
    sym = os.path.basename(paths[0]).split("_")[0]
    if not paths[0].endswith("_1h.csv"):
        # the engine hardcodes the 1h file (D1H) and never reads any other
        # timeframe: a non-1h input gets hashed as provenance but never used,
        # which minted duplicate 15m artifacts with identical 1h numbers
        # (2026-10-31 external audit). Fail loudly instead.
        raise ValueError(
            f"botstrat only runs the 1h file; got {os.path.basename(paths[0])} "
            "(the engine hardcodes data/binance_klines_1h)")
    r = B.run(sym, B.load(sym))
    eq, tr_, w_, gp, gl, mdd = (float(r[0]), int(r[1]), int(r[2]),
                                float(r[3]), float(r[4]), float(r[5]))
    metrics = {
        "n_trades": tr_, "return_pct": (eq / 10000.0 - 1.0) * 100.0, "final_equity": eq,
        "win_rate": w_ / max(tr_, 1),
        "profit_factor": gp / gl if gl > 0 else (float("inf") if gp > 0 else 0.0),
        "gross_profit": gp, "gross_loss": gl, "max_dd_pct": -mdd * 100.0, "flag": _flag(tr_),
    }
    return metrics, {"adapter": "botstrat", "engine_version": "botstrat"}, None


def run_ffs(paths, params):
    F2 = _load_module(os.path.join(CODE, "ffs_engine2.py"), "ffs_engine2")
    df = pd.read_csv(paths[0]).sort_values("open_ts").reset_index(drop=True)
    eq, pf, wr, n, mdd100, _trades = F2.engine2(df)[:6]
    eq, n = float(eq), int(n)
    metrics = {
        "n_trades": n, "return_pct": (eq / 10000.0 - 1.0) * 100.0, "final_equity": eq,
        "profit_factor": float(pf), "win_rate": float(wr) / 100.0,
        "max_dd_pct": -float(mdd100), "flag": _flag(n),
    }
    return metrics, {"adapter": "ffs", "engine_version": "ffs"}, None


def run_mp20(paths, params):
    M = _load_module(os.path.join(CODE, "mp20_report_ports.py"), "mp20_report_ports")
    want = params.get("window", "FULL")
    D, ts = M.load_universe()
    P_full = M.panel(D, ts)
    I_full = M.precompute(P_full, len(ts))
    N = len(ts)
    rows, b = M.run_window(P_full, I_full, N, want)
    tables = []
    for m in rows:
        tables.append({"id": m["id"], "name": m["name"], "ret_pct": float(m["ret"]),
                       "pf": float(m["pf"]), "wr_pct": float(m["wr"]), "n": int(m["n"]),
                       "dd_pct": float(m["dd"]), "sharpe": float(m["sharpe"])})
    metrics = {"window": want, "n_strategies": len(tables),
               "bench_ret_pct": float(b["ret"]), "bench_dd_pct": float(b["dd"])}
    return metrics, {"adapter": "mp20", "engine_version": "mp20"}, tables


def run_emaadx(paths, params):
    """EMA Cross + ADX [Quant] port — Pine v6, process_orders_on_close=true.
    Known-answer audited by code/_emaadx_audit.py before any real-data run."""
    sys.path.insert(0, CODE)
    import importlib
    m = importlib.import_module("emaadx_engine")
    out = m.run_symbol(paths[0], dict(params))
    return (out["metrics"],
            {"adapter": "emaadx", "engine_version": "emaadx-1"},
            out["tables"])


def run_mps20(paths, params):
    """20-strategy multi-pair suite (CLAUDE BOT STRATEGIES 1.zip), author code
    in code/claude_bot_1/ with a minimal ONE-CLASS fix: same-bar candidate
    sets were iterated in process-dependent (PYTHONHASHSEED) order, so fills
    at the same bar could be created in a different order per process and
    float sums (fees, concentration) diverged in the last bits ->
    `verify` refused every artifact. Fixed by replacing the candidate SETS in
    sig_01/sig_11 with the ranked lists they came from (order = ranking), and
    the high_vol/low_vol tercile sets in sig_14 with ranked-order lists
    (ties in max()/min() resolve to the first pair in volatility-ascending
    rank order). No signal thresholds or sizing changed; known-answer audit
    code/_claude_audit.py passes 7/7 on the fixed bytes. Verify re-runs the
    engine in a fresh process, so an OK verify is itself the cross-process
    determinism proof."""
    sys.path.insert(0, CODE)
    import importlib
    m = importlib.import_module("mps20_engine")
    src_paths = {}
    for p in paths:
        base = os.path.basename(p)
        src_paths[base.split("_")[0]] = p
    out = m.run_suite(src_paths, dict(params))
    return (out["metrics"],
            {"adapter": "mps20", "engine_version": "mps20-1"},
            out["tables"])


def run_mpv3(paths, params):
    """MP-V3 portfolio adapter running code/mpv3_engine.py."""
    sys.path.insert(0, CODE)
    import importlib
    m = importlib.import_module("mpv3_engine")
    return m.run_mpv3(paths, dict(params))


def run_pack50(paths, params):
    """Fifty-strategy prompt pack (Downloads/50_strategies_crypto-claude1.md).

    One numbered prompt per artifact. The engine measures both the pack's own
    cost block and the repo gate cost inside the same artifact, charges funding
    at the settlement instants, and reports the 70/30 split the prompt asks for.
    S34 and S49 need NVDA data that is not on disk and are never estimated."""
    sys.path.insert(0, CODE)
    import importlib
    m = importlib.import_module("pack50_engine")
    return m.run_one(paths, dict(params))


def run_pack50b(paths, params):
    """Fifty-strategy prompt pack, claude2 edition
    (Downloads/crypto_strategy_prompts_50-claude2.md, S01-S25 / D01-D25).

    Same one-prompt-per-artifact protocol as pack50, reusing the frozen
    pack50_core execution machinery: pack cost block (5.0 fee + 2.0 slip bps
    per side), repo gate cost and zero-cost control measured inside each
    artifact, funding charged at the settlement instants, 70/30 split, gates
    G1-G6. S08/S23/D08/D18 need NVDA data that is not on disk and are never
    estimated. SPXUSDT ("SPCX") exists only as plain 1m/1h klines."""
    sys.path.insert(0, CODE)
    import importlib
    m = importlib.import_module("pack50b_engine")
    return m.run_one(paths, dict(params))


def run_gatecal(paths, params):
    """Calibration of the gate set itself: seeded random-entry null books on
    real BTCUSDT 1h prices, run through the audited pack50_core execution
    core, scored under both the v1 (G1-G6) and the v2 statistical gates.
    Measures the false-positive rate at zero planted edge and the power curve
    at 5/10/20 bps planted edge (audit C1)."""
    sys.path.insert(0, CODE)
    import importlib
    m = importlib.import_module("gatecal_engine")
    return m.run_one(paths, dict(params))


def run_gate2(paths, params):
    """v2 gate scoring of a pack50b prompt: same frozen rules and execution
    core, measured with gate2.py's statistical layer (expectancy bootstrap,
    purged folds, monthly buckets, beta alpha, top-5% concentration,
    breakeven cost, P95 drawdown)."""
    sys.path.insert(0, CODE)
    import importlib
    m = importlib.import_module("gate2_engine")
    return m.run_one(paths, dict(params))


_GATECAL_INPUTS_FILES = [("binance_klines_1h_taker", "BTCUSDT_1h.csv")]


def _gatecal_inputs(tf, sym):
    out = [os.path.join(DATA, d, f) for d, f in _GATECAL_INPUTS_FILES]
    p = os.path.join(DATA, "binance_funding", "BTCUSDT_funding.json")
    if os.path.exists(p):
        out.append(p)
    return out


_PACK50_DIR = {
    "1m": ("binance_klines_1m_taker", "1m"),
    "3m": ("binance_klines_1m_taker", "1m"),
    "5m": ("binance_klines_5m_taker", "5m"),
    "15m": ("binance_klines_15m_taker", "15m"),
    "30m": ("binance_klines_15m_taker", "15m"),
    "1h": ("binance_klines_1h_taker", "1h"),
    "4h": ("binance_klines_1h_taker", "1h"),
    "1d": ("binance_klines_1h_taker", "1h"),
}

# SPXUSDT has no taker klines on disk: its plain 1m/1h files are the only
# series, and the 5m/15m prompts resample from the 1m file.
_PACK50B_SPX = {"1m": ("binance_klines_1m", "1m"),
                "3m": ("binance_klines_1m", "1m"),
                "5m": ("binance_klines_1m", "1m"),
                "15m": ("binance_klines_1m", "1m"),
                "30m": ("binance_klines_1m", "1m"),
                "1h": ("binance_klines_1h", "1h")}


def _pack50b_inputs(tf, sym):
    """Klines for every leg first, then the funding files that exist on disk.

    Same contract as _pack50_inputs: the pair legs are hashed in a fixed order
    and the file names carry the native timeframe, which pack50b_engine reads."""
    legs = sym.split("+")
    out = []
    for s in legs:
        if s == "SPXUSDT":
            d, base = _PACK50B_SPX[tf]
        else:
            d, base = _PACK50_DIR[tf]
        out.append(os.path.join(DATA, d, f"{s}_{base}.csv"))
    for s in legs:
        p = os.path.join(DATA, "binance_funding", f"{s}_funding.json")
        if os.path.exists(p):
            out.append(p)
    return out


def run_pack50c(paths, params):
    """Qwen fifty-prompt pack (Downloads/Qwen_50 strategies.txt, Q01-Q50).

    One numbered prompt per artifact, measured with BOTH the pack50b protocol
    (pack cost block 5.0+2.0 bps, repo gate cost, zero-cost control, funding
    at the settlement instants, v1 gates G1-G6) and the v2 statistical layer
    (expectancy bootstrap, purged split/folds, exit-month buckets, top-5%
    concentration trio, cost share, P95 drawdown, MAE/liquidation). Eight NVDA
    prompts are NO DATA and are never estimated; "SPCX" reads as SPXUSDT."""
    sys.path.insert(0, CODE)
    import importlib
    m = importlib.import_module("pack50c_engine")
    return m.run_one(paths, dict(params))


def run_pack50d(paths, params):
    """DeepSeek fifty-prompt pack (Downloads/deepseek_markdown_20261027_68930c.md,
    P01-P50). Same one-prompt-per-artifact protocol as pack50c: pack cost block
    (5.0 + 2.0 bps), repo gate cost / 2x / breakeven / zero-cost controls,
    funding at the settlement instants, v1 gates G1-G6 AND the v2 statistical
    layer inside each artifact. Two NVDA prompts are NO DATA. P23's BTC filter
    leg and P17's pair legs are hashed into the artifact inputs."""
    sys.path.insert(0, CODE)
    import importlib
    m = importlib.import_module("pack50d_engine")
    return m.run_one(paths, dict(params))


def run_pack100(paths, params):
    """Sonnet 100-prompt pack (Downloads/strategy_prompts_100-sonnet-claude.md,
    numbered 01..100). One artifact per (prompt, timeframe) cell -- the pack's
    own template says "5m-15m-1h" runs the three timeframes separately. The
    pack declares NO cost block, so the primary headline IS the repo gate
    (5.0 fee + 0.5 slip bps per side), with 2x / breakeven / zero-cost
    controls, funding at the settlement instants, the v1 gates G1-G6 AND the
    pack50d v2 statistical gate definitions inside every artifact. NVDA legs,
    open interest, the long/short ratio and JUP funding have no history on
    disk: those prompts are NO DATA, never estimated. Multi-leg prompts (51,
    89: BTC aux leg; 99, 100: ratio pairs) hash every leg into the inputs."""
    sys.path.insert(0, CODE)
    import importlib
    m = importlib.import_module("pack100_engine")
    return m.run_one(paths, dict(params))


def _pack100_inputs(tf, sym):
    """pack50b's file mapping; SPCX -> SPXUSDT; pair/aux legs keep their order."""
    return _pack50b_inputs(tf, sym.replace("SPCX", "SPXUSDT"))


def run_qs(paths, params):
    """Strategy-catalog family A (QS-001..QS-010) under the catalog's own
    G1-G7 contract: 1%-risk sizing with gross cap and risk devices, next-open
    taker fills with gap-aware stop-market stops, SL-first ties, the declared
    cost ladder (Base 14 / Adverse 22 / Stress 35 bps RT + the 11 bps repo
    gate point), realized funding at settlement instants, five walk-forward
    folds plus a once-opened 20% holdout with embargo and purge, truncation
    causality, PSR, a seeded random-entry null per cell, and G7 gate
    verdicts. Variants: two-sided and long-only, separate hypotheses."""
    sys.path.insert(0, CODE)
    import importlib
    m = importlib.import_module("qs_run")
    return m.run_one(paths, dict(params))


def _qs_inputs(tf, sym):
    return [os.path.join(DATA, f"binance_klines_{tf}_taker", f"{sym}_{tf}.csv"),
            os.path.join(DATA, "binance_funding", f"{sym}_funding.json")]


def run_qsf(paths, params):
    """Strategy-catalog trade-flow hypotheses (QS-043/044/048/049/050/053/
    058/093, the eight PARTIAL TK strategies) under the same G1-G7 contract
    as family A. Bar-level taker flow from the kline taker fields (imbalance,
    CVD delta, sell share) — the catalog's own PARTIAL approximation, labeled
    as such. The catalog's calibration grids remain unswept (fixed rules)."""
    sys.path.insert(0, CODE)
    import importlib
    import qs_flow_strats          # registers into qs_strats.SPECS
    m = importlib.import_module("qs_run")
    return m.run_one(paths, dict(params))


def _qsf_inputs(tf, sym):
    return [os.path.join(DATA, f"binance_klines_{tf}_taker", f"{sym}_{tf}.csv"),
            os.path.join(DATA, "binance_funding", f"{sym}_funding.json")]


def run_qsb(paths, params):
    """Strategy-catalog family B (QS-011..QS-020: RSI, Bollinger, z-score,
    AVWAP day/week, VWAP-ATR, displacement fade, range oscillation,
    vol-expansion fade, the QS-019 OU BTC/ETH pair, wick fade) under the
    same G1-G7 contract as families A and flow. QS-019 routes to
    qs_pair_run (dollar-neutral two-leg execution, funding on both legs,
    A/B-ratio benchmark); the rest to qs_run. The catalog's calibration
    grids remain unswept (fixed rules)."""
    sys.path.insert(0, CODE)
    import importlib
    import qs_b_strats            # registers into qs_strats.SPECS
    sid = str(params.get("strat", ""))
    m = importlib.import_module("qs_pair_run" if sid == "QS-019" else "qs_run")
    return m.run_one(paths, dict(params))


def run_qsc(paths, params):
    """Strategy-catalog family C (QS-021..QS-030, volatility and breakout:
    ATR compression, BB squeeze, realized-vol regime, opening range,
    Donchian+volume, NR7 expansion, chandelier stop-and-reverse, failed
    breakout, breakout-retest, HTF-regime breakout) under the same G1-G7
    contract as families A and B. QS-024 trades BTC/ETH/SOL on 5m/15m
    only (the catalog's own instrument restriction); QS-030's higher-
    timeframe regime is resampled from the same klines (closed bars only)."""
    sys.path.insert(0, CODE)
    import importlib
    import qs_c_strats            # registers into qs_strats.SPECS
    m = importlib.import_module("qs_run")
    return m.run_one(paths, dict(params))


def _qsc_inputs(tf, sym):
    return [os.path.join(DATA, f"binance_klines_{tf}_taker", f"{sym}_{tf}.csv"),
            os.path.join(DATA, "binance_funding", f"{sym}_funding.json")]


def run_qsd(paths, params):
    """Strategy-catalog family D (QS-031..QS-040, market structure and
    price action: confirmed swing breakouts, trend-structure continuation,
    CHoCH reversal, S/R zone rejection, range sweeps, pivot breakout-retest,
    range compression, momentum-exhaustion fade, MTF structural alignment,
    displacement continuation) under the same G1-G7 contract as families
    A-C. All pivots carry the k=3 confirmation delay (a pivot is known only
    k bars after its bar closes); QS-039's higher-timeframe structure is
    resampled from the same klines (closed HTF bars only)."""
    sys.path.insert(0, CODE)
    import importlib
    import qs_d_strats            # registers into qs_strats.SPECS
    m = importlib.import_module("qs_run")
    return m.run_one(paths, dict(params))


def _qsd_inputs(tf, sym):
    return [os.path.join(DATA, f"binance_klines_{tf}_taker", f"{sym}_{tf}.csv"),
            os.path.join(DATA, "binance_funding", f"{sym}_funding.json")]


def _qsb_inputs(tf, sym):
    if "+" in sym:                # QS-019 pair: two legs, two funding files
        a, b = sym.split("+")
        return [os.path.join(DATA, f"binance_klines_{tf}_taker", f"{a}_{tf}.csv"),
                os.path.join(DATA, f"binance_klines_{tf}_taker", f"{b}_{tf}.csv"),
                os.path.join(DATA, "binance_funding", f"{a}_funding.json"),
                os.path.join(DATA, "binance_funding", f"{b}_funding.json")]
    return [os.path.join(DATA, f"binance_klines_{tf}_taker", f"{sym}_{tf}.csv"),
            os.path.join(DATA, "binance_funding", f"{sym}_funding.json")]


def _pack50c_inputs(tf, sym):
    """pack50b's file mapping with the SPCX -> SPXUSDT translation applied."""
    return _pack50b_inputs(tf, sym.replace("SPCX", "SPXUSDT"))


def _pack50d_inputs(tf, sym):
    """pack50b's file mapping; SPCX -> SPXUSDT; pair/aux legs keep their order."""
    return _pack50b_inputs(tf, sym.replace("SPCX", "SPXUSDT"))


# ══════════════════════════════════════════════════════ cand7
_CAND7_LEGS = {
    "ETHUSDT": ["ETHUSDT"],                 # C1 and C3 share the inputs
    "SOLUSDT": ["SOLUSDT"],                 # C2 and C7 share the inputs
    "BASKET5": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "SUIUSDT", "XRPUSDT"],
    "SOLUSDT+BTCUSDT": ["SOLUSDT", "BTCUSDT"],
}


def _cand7_inputs(tf, sym):
    legs = _CAND7_LEGS[sym]
    out = [os.path.join(DATA, "binance_klines_1h_taker", f"{s}_1h.csv") for s in legs]
    for s in legs:
        p = os.path.join(DATA, "binance_funding", f"{s}_funding.json")
        if os.path.exists(p):
            out.append(p)
    return out


def run_cand7(paths, params):
    """The seven prespecified candidates of `strategy_candidates_v2-claude.md`
    (2026-10-27).  One artifact per candidate; the declared cost block drives
    the headline, and the repo cost, the old 22 bps preset, a zero-cost control,
    full-equity sizing (directional books), the v1 gates and the v2 statistical
    layer are measured inside the same artifact."""
    sys.path.insert(0, CODE)
    import importlib
    m = importlib.import_module("cand7_engine")
    return m.run_one(paths, dict(params))


def run_rsimr(paths, params):
    """RSI(14) mean-reversion on SOL/USDC spot 1h (user-prespecified, no tuning):
    entry flat & RSI<30 at close -> next open; exit RSI>70 -> next open;
    ATR(14)*2 stop from the fill, stop-first, gap-through at the open;
    sizing 1% of equity risked to the stop, spot (no leverage, long only);
    repo costs 5+0.5 bps/side with the zero-cost control in-artifact.
    Audited by code/_rsi_mr_audit.py; data manifest data/SOLUSDC_IMPORT.json."""
    sys.path.insert(0, CODE)
    import importlib
    m = importlib.import_module("rsi_mr_engine")
    out = m.run_symbol(paths[0], dict(params))
    return (out["metrics"],
            {"adapter": "rsimr", "engine_version": "rsi-mr-1",
             "data_manifest": "data/SOLUSDC_IMPORT.json"},
            out["tables"])


def run_eqpack(paths, params):
    """cbpack's ten rule strategies on ALPACA EQUITIES daily bars (first
    equities campaign).  The engine is code/cbpack_engine.py UNMODIFIED -- the
    hash-locked, historically audited executor -- so only the data and the
    declared cost regime change.  Audited before any real-data artifact by
    code/_eqpack_audit.py (E1-E7); data manifest data/ALPACA_EQUITIES_IMPORT.json.

    Declared adaptations, uniform across every strategy (no per-strategy picks):
      * htf   : strategies whose signature has an `htf` parameter get
                htf=1440 minutes, which on daily bars reproduces EXACTLY the
                pack's own 1h-campaign semantics (there htf=60min == chart tf:
                sign of EMA20 vs EMA50 of the same closes, shifted one bar).
      * flow  : equities carry no taker-buy split, so the pack's own declared
                fallback applies: flow_source = candle_proxy
                (volume * sign(close-open) / sma(volume,50)).
      * S06   : EXCLUDED -- intraday UTC sessions do not exist on daily bars.
      * S07/S08: self-skip through the pack's requires check (no funding_rate
                / open_interest column on equities).
    Costs (per side): 'eq' = 0.1 bps fee + 0.5 bps slippage (Alpaca: zero
    commission, SEC/TAF amortised, liquid-ETF spread); 'cons' = 1 + 1 bps;
    the zero-cost control runs inside every artifact (drag_pp measured, not
    derived).  Sizing is the pack's own default (stop_risk 1%, max leverage 3x).
    """
    import inspect
    pack = _load_module(os.path.join(CODE, "cbpack_engine.py"), "cbpack_engine")
    p = dict(params)
    costs_key = str(p.pop("costs", "eq"))
    htf_minutes = int(p.pop("htf_minutes", 1440))
    if p:
        raise ValueError(f"unknown eqpack params: {sorted(p)}")
    _COSTS = {"eq": (0.1, 0.5), "cons": (1.0, 1.0), "zero": (0.0, 0.0)}
    if costs_key not in _COSTS:
        raise ValueError(f"eqpack costs: use one of {sorted(_COSTS)}")
    fee, slip = _COSTS[costs_key]

    raw = pd.read_csv(paths[0])
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    idx = pd.to_datetime(raw["open_ts"], unit="ms", utc=True)
    df = pack.prepare(raw.set_index(idx))
    sym = os.path.basename(paths[0]).split("_")[0]
    cfg = pack.BacktestConfig(fee_bps=fee, slippage_bps=slip)
    zcfg = pack.BacktestConfig(fee_bps=0.0, slippage_bps=0.0)
    flow_source = pack.flow_series(df)[1]

    RUN = ["S01", "S02", "S03", "S04", "S05", "S09", "S10"]
    rows = []
    for sid in RUN:
        spec = pack.STRATEGIES[sid]
        missing = set(spec.requires) - set(df.columns)
        if missing:
            rows.append({"id": sid, "name": spec.name, "status": f"SKIPPED: missing {sorted(missing)}"})
            continue
        kw = {"htf": htf_minutes} if "htf" in inspect.signature(spec.fn).parameters else {}
        sig = pack.make_signals(df, sid, **kw)
        r = pack.backtest(df, sig, cfg)
        z = pack.backtest(df, sig, zcfg)
        m = r.metrics
        tr = r.trades
        pnl = tr["pnl"].to_numpy(float)
        total = float(pnl.sum())
        pos = np.sort(pnl[pnl > 0])[::-1] if len(pnl) else np.zeros(0)
        top5 = float(pos[:5].sum())
        conc_share = (100.0 * top5 / total) if total > 0 else None
        conc_without = (100.0 * (total - top5) / total) if total > 0 else None
        gross_usd = m["gross_return_pct"] / 100.0 * cfg.initial_capital
        cost_share = (100.0 * m["fees_paid"] / gross_usd) if gross_usd > 0 else None

        eq = r.equity
        vals = eq.notna().to_numpy()
        i0, i1 = int(np.argmax(vals)), len(vals) - 1 - int(np.argmax(vals[::-1]))
        mid = (i0 + i1) // 2
        e = eq.to_numpy(float)
        ret_h1 = 100.0 * (e[mid] / e[i0] - 1.0) if e[i0] > 0 else 0.0
        ret_h2 = 100.0 * (e[i1] / e[mid] - 1.0) if e[mid] > 0 else 0.0
        yr = {}
        for j in range(i0, i1 + 1):
            y = df.index[j].year
            yr.setdefault(y, []).append(e[j])
        year_rets = {y: 100.0 * (v[-1] / v[0] - 1.0) for y, v in sorted(yr.items())
                     if len(v) >= 2 and v[0] > 0}
        n_green = sum(1 for x in year_rets.values() if x > 0)
        pf = m["profit_factor"]
        rows.append({
            "id": sid, "name": spec.name, "status": "ok",
            "trades": m["n_trades"], "net_%": m["net_return_pct"],
            "gross_%": m["gross_return_pct"], "buy_hold_%": m["buy_hold_return_pct"],
            "excess_%": m["excess_vs_buy_hold_pct"], "maxDD_%": m["max_drawdown_pct"],
            "win_%": m["win_rate_pct"],
            "PF": (None if pf in (float("inf"), float("-inf")) else pf),
            "exp_R": m["expectancy_R"], "sharpe": m["sharpe_annualised"],
            "exposure_%": m["exposure_pct"], "avg_bars": m.get("avg_bars_in_trade"),
            "drag_pp": (z.metrics["net_return_pct"] - m["net_return_pct"]),
            "conc_top5_share_pct": conc_share, "conc_net_without_top5_pct": conc_without,
            "ret_h1_pct": ret_h1, "ret_h2_pct": ret_h2,
            "n_green_years": n_green, "n_years": len(year_rets),
            "fees_paid": m["fees_paid"], "cost_gross_pct": cost_share,
            "htf_minutes": (htf_minutes if kw else None),
            "exit_reasons": m["exit_reasons"],
            "year_returns": year_rets,
            "gates_pass": bool(pf is not None and pf > 1.2 and m["n_trades"] >= 30
                               and (conc_share is None or conc_share < 100.0)
                               and (cost_share is None or cost_share < 40.0)
                               and len(year_rets) and n_green / len(year_rets) >= 2 / 3),
        })
    for sid in ("S06", "S07", "S08"):
        spec = pack.STRATEGIES[sid]
        why = ("intraday UTC session strategy; daily bars carry no session "
               "structure (declared exclusion)" if sid == "S06"
               else f"SKIPPED: missing {sorted(set(spec.requires) - set(df.columns))}")
        rows.append({"id": sid, "name": spec.name, "status": why})

    ok_rows = [r for r in rows if r["status"] == "ok"]
    bh = ok_rows[0]["buy_hold_%"] if ok_rows else None
    metrics = {
        "symbol": sym, "bars": int(len(df)),
        "first": str(df.index[0].date()), "last": str(df.index[-1].date()),
        "costs": costs_key, "fee_bps_per_side": fee, "slip_bps_per_side": slip,
        "cost_bp_roundtrip": 2.0 * (fee + slip),
        "htf_minutes_declared": htf_minutes, "flow_source": flow_source,
        "sizing": "pack default: stop_risk 1%, max leverage 3x",
        "n_run": len(ok_rows), "n_excluded": len(rows) - len(ok_rows),
        "bh_return_pct": bh,
        "n_net_positive": sum(1 for r in ok_rows if r["net_%"] > 0),
        "n_pf_gt_1p2_n30": sum(1 for r in ok_rows
                               if r["PF"] and r["PF"] > 1.2 and r["trades"] >= 30),
        "n_pass_all_gates": sum(1 for r in ok_rows if r["gates_pass"]),
        "n_beat_bh": sum(1 for r in ok_rows if r["excess_%"] > 0),
        "best_net_pct": max((r["net_%"] for r in ok_rows), default=None),
        "best_net_id": next((r["id"] for r in ok_rows
                             if r["net_%"] == max((x["net_%"] for x in ok_rows),
                                                  default=None)), None),
        "engine_note": "cbpack_engine.py used UNMODIFIED (hash-locked); "
                       "audit code/_eqpack_audit.py E1-E7",
    }
    tables = [{"kind": "strategy", **{k: v for k, v in r.items()}} for r in rows]
    return metrics, {"adapter": "eqpack", "engine_version": "cbpack-1-eq",
                     "source_file": "code/cbpack_engine.py (unmodified)",
                     "data_manifest": "data/ALPACA_EQUITIES_IMPORT.json",
                     "costs": {"fee_bps": fee, "slippage_bps": slip},
                     "adaptations": {"htf_minutes": htf_minutes,
                                     "flow_source": flow_source,
                                     "excluded": ["S06 sessions", "S07 funding",
                                                  "S08 OI"]}}, tables


def _pack50_inputs(tf, sym):
    """Klines for every leg first, then the funding files that exist on disk.

    `sym` carries the pair, e.g. "SOLUSDT+ETHUSDT", so the pair legs are hashed
    into the artifact in a fixed order and the run_id cannot be ambiguous."""
    d, base = _PACK50_DIR[tf]
    legs = sym.split("+")
    out = [os.path.join(DATA, d, f"{s}_{base}.csv") for s in legs]
    for s in legs:
        p = os.path.join(DATA, "binance_funding", f"{s}_funding.json")
        if os.path.exists(p):
            out.append(p)
    return out


def _cbot_timing(tf: str, hold_mode: str) -> dict:
    """Walk-forward + hold timing, derived per timeframe.

    A literal 60-day train window at 1h is 1440 bars and at 1m is 86400, so one
    constant cannot serve both. 5m is special-cased to the pack's shipped
    defaults (17500/1000/5000) so the already-published 5m artifacts still
    verify; every other timeframe derives from the same 60-day rule.
    """
    interval = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}[tf]
    if hold_mode == "minutes":
        hb = max(1, int(round(15.0 / interval)))
    else:
        hb = 3
    if interval == 5:
        train, refit, min_train = 17500, 1000, 5000
    else:
        train = 60 * 24 * 60 // interval
        refit = int(round((1000.0 / 288.0) * 24 * 60 / interval))
        min_train = int(round(train * 0.286))
    return {"interval_min": interval, "horizon_bars": hb, "train_bars": train,
            "refit_every": refit, "min_train": min_train}


def run_cbot(paths, params):
    from dataclasses import replace
    sys.path.insert(0, CODE)
    from cbot.config import BotConfig
    from cbot.suite import run_suite

    p = dict(params)
    tf = p.pop("tf")
    hold_mode = p.pop("hold_mode", "bars")
    slice_from = p.pop("slice_from", None)
    slice_to = p.pop("slice_to", None)

    df = pd.read_csv(paths[0])
    df.columns = [c.strip() for c in df.columns]
    df = df.set_index(pd.to_datetime(df["open_ts"], unit="ms", utc=True))
    df = df[["open", "high", "low", "close", "volume", "taker_buy_base"]].astype(float)
    df = df.sort_index()
    # A cbot slice carries a WARMUP before the scored region. That is not a guess:
    # `code/_xtf_periods.py`, which generated the period runs, says so in its own
    # docstring -- "Each slice keeps TRAIN_DAYS of warmup before the scored region
    # (see run_cbot), so slicing shrinks the evaluation window WITHOUT starving the
    # model of training data."  TRAIN_DAYS was a constant of the lost harness; it is
    # recovered here from the twelve slice artifacts, all of which start exactly
    # 63.00 days before their recorded slice_from, at midnight UTC
    # (2025-06-14 -> 2025-04-12, 2026-02-13 -> 2025-12-12, 2025-11-14 -> 2025-09-12,
    # 2026-04-30 -> 2026-02-26); each symbol's first slice simply clamps to the data
    # start.  slice_to is NOT moved, so `slice_from` keeps meaning "start of the
    # scored region" -- which is what the campaign report's period labels say.
    # Without this warmup the adapter reproduces only the first slice of each symbol.
    TRAIN_DAYS = 63
    if slice_from:
        t0 = pd.Timestamp(slice_from, tz="UTC") - pd.Timedelta(days=TRAIN_DAYS)
        df = df[df.index >= t0]
    if slice_to:
        df = df[df.index < pd.Timestamp(slice_to, tz="UTC")]
    if len(df) < 1000:
        raise ValueError(f"only {len(df)} bars after slicing -- not enough to test")

    timing = _cbot_timing(tf, hold_mode)
    sym = os.path.basename(paths[0]).split("_")[0]
    cfg = BotConfig(symbol=sym, **timing)
    res = run_suite(df, cfg, n_perm=5, seed=0)

    def _v(x):
        # type-preserving: `trades` is an int in the artifacts and a float cast
        # would change the bytes (and so break verify) without changing the value.
        if isinstance(x, (bool, np.bool_)):
            return bool(x)
        if isinstance(x, str):
            return x
        if isinstance(x, (int, np.integer)):
            return int(x)
        x = float(x)
        return x if np.isfinite(x) else float("nan")

    tables = [{k.lower(): _v(v) for k, v in row.items()}
              for row in res.to_dict(orient="records")]
    # `best_net_ret` is the return OF THE BEST-t ROW, not the largest return in the
    # table. Recovered from the artifacts: in every cbot artifact
    # best_net_ret_id == best_net_t_id, including rows where another strategy had a
    # bigger net_ret (BTC 15m: S05 t=5.19 ret=2.90% beats S02 ret=9.79%).
    best_t = max(tables, key=lambda r: (r["net_t"] if np.isfinite(r["net_t"]) else -np.inf))
    aucs = [r["auc"] for r in tables if np.isfinite(r["auc"])]
    hold_min = timing["horizon_bars"] * timing["interval_min"]
    cost_bp = (2.0 * (cfg.fee_taker + cfg.slippage)
               + cfg.funding_8h * (hold_min / 480.0)) * 1e4
    metrics = {
        "n_strategies": len(tables), "n_pass": int(sum(1 for r in tables if r["pass"])),
        "n_bars": int(len(df)), "horizon_bars": timing["horizon_bars"],
        "hold_minutes": hold_min, "train_bars": timing["train_bars"],
        "cost_bp_roundtrip": float(cost_bp),
        "t_crit_bonferroni": float(res.attrs["tcrit"]),
        "best_net_t": _v(best_t["net_t"]), "best_net_t_id": best_t["id"],
        "best_net_ret_pct": _v(best_t["net_ret"]) * 100.0, "best_net_ret_id": best_t["id"],
        "max_trades": int(max(r["trades"] for r in tables)),
        "min_auc": _v(min(aucs)), "max_auc": _v(max(aucs)),
        "bh_return_pct": _v(tables[0]["bh_ret"]) * 100.0,
    }
    prov = {"adapter": "cbot", "engine_version": "cbot-1", "derived_timing": timing,
            "n_perm": 5, "seed": 0}
    return metrics, prov, tables


def run_xrpneutral(paths, params):
    """The DELTA-NEUTRAL XRP book (code/xrp_neutral_engine.py) as an adapter.

    This is the FORWARD PAPER BOT's engine, registered so its numbers stop living
    in a status file on a VPS and start living in an artifact that `verify` can
    reproduce and `guard` can back.

    The engine is deliberately NOT grid_audit.simulate: that file is the validated
    long-grid engine behind 300+ artifacts, and adding a `side` flag to it would
    change its bytes and silently invalidate the forward record of a bot that is
    still running. This repo already paid for that class of mistake once (the
    grid_core refactor: 11,966 fills against the validator's 5,233).

    Everything the report claims is MEASURED HERE, not derived in prose:

      * concentration  -> best5_share_pct, net_without_best5_pct
      * significance   -> a 20,000-draw bootstrap of the mean per trade, seeded 7
                          (the same stream the gauntlet used, so the numbers are
                          identical rather than "close")
      * period split   -> period1/2/3_pct, n_periods_green
      * neutrality     -> avg_abs_delta_pct, max_abs_delta_pct, and a LONG-ONLY
                          control in the same artifact: if the two-sided book only
                          matched the long-only one, "neutral" would be a label
      * funding        -> funding_paid AND funding_covers_bars, because a partial
                          funding history silently changes the equity (it made the
                          deployed bot read -$49.96 instead of +$266.14)

    Params (all optional; the defaults are v1's 10,000 USDT / 0.25x book, so the
    v1 artifact still verifies bit-for-bit). The deployed v2 passes
    init=25, equity_pct=1.0, delta_max_pct=2.0, leverage=10 explicitly:
      trend_band, stop_atr_mult, cover_mult, delta_max_pct,
      init, equity_pct, leverage,
      fee_bps, flat_fee_bps, slip_bps, funding, control_long_only,
      slice_from, slice_to
    """
    # A FRESH instance: the sizing below mutates EQUITY_PCT, and the cached
    # module would carry that into every later run in this process.
    p = dict(params)
    # Which engine file to load. A PRIVATE param, injected by the wrappers
    # below and never stored: params ARE hashed into run_id, so a stored
    # `_engine_file` would make one book key differently per variant.
    engine_file = p.pop("_engine_file", "xrp_neutral_engine.py")
    X = _load_fresh(os.path.join(CODE, engine_file),
                    "xrpneutral_" + os.path.splitext(engine_file)[0])
    tf = p.pop("tf", "15m")
    if tf != "15m":
        raise ValueError(f"xrpneutral is a 15m book; the deployed bot runs 15m, got {tf!r}")
    init = float(p.pop("init", X.INIT))
    equity_pct = float(p.pop("equity_pct", X.EQUITY_PCT))
    leverage = float(p.pop("leverage", X.LEVERAGE))
    X.EQUITY_PCT = equity_pct
    X.LEVERAGE = leverage
    trend_band = float(p.pop("trend_band", 0.10))
    stop_atr_mult = float(p.pop("stop_atr_mult", 0.5))
    cover_mult = float(p.pop("cover_mult", 1.0))
    delta_max_pct = float(p.pop("delta_max_pct", 0.50))
    fee_bps = float(p.pop("fee_bps", X.MAKER_FEE * 1e4))
    flat_fee_bps = float(p.pop("flat_fee_bps", X.TAKER_FEE * 1e4))
    slip_bps = float(p.pop("slip_bps", X.FLAT_SLIP * 1e4))
    use_funding = bool(p.pop("funding", True))
    want_control = bool(p.pop("control_long_only", True))
    slice_from = p.pop("slice_from", None)
    slice_to = p.pop("slice_to", None)
    fill_1m = bool(p.pop("fill_1m", False))
    if p:
        raise ValueError(f"unknown xrpneutral params: {sorted(p)}")

    # Funding is a required input, not an optional one: this book is worth running
    # because a balanced perp position pays ~no funding, and that claim is only
    # testable if the real settlements are present.
    klines = paths[0]
    funding_path = paths[1] if len(paths) > 1 else None
    if use_funding and not funding_path:
        raise FileNotFoundError("xrpneutral needs binance_funding/<SYM>_funding.json")

    # The 1m tape is located BY NAME, not by index: the 15m artifact and the 1m
    # artifact share this runner, and an index would silently bind the wrong
    # file the first time an input is added.
    one_m_path = None
    if fill_1m:
        one_m_path = next((q for q in paths if q.lower().endswith("_1m.csv")), None)
        if not one_m_path:
            raise FileNotFoundError(
                "xrpneutral1m needs data/binance_klines_1m/<SYM>_1m.csv as an input")

    raw = pd.read_csv(klines)
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    raw = raw.sort_values("open_ts")
    ts = pd.to_datetime(raw["open_ts"], unit="ms", utc=True)
    if slice_from:
        raw = raw[ts >= pd.Timestamp(slice_from, tz="UTC")]
        ts = ts.loc[raw.index]
    if slice_to:
        raw = raw[ts < pd.Timestamp(slice_to, tz="UTC")]
    if len(raw) < 2000:
        raise ValueError(f"only {len(raw)} bars after slicing -- not enough to test")
    bars = [(int(r.open_ts), float(r.open), float(r.high), float(r.low),
             float(r.close), float(r.volume)) for r in raw.itertuples(index=False)]
    sym = os.path.basename(klines).split("_")[0]

    fund_dir = os.path.dirname(funding_path) if funding_path else None
    fund_cfg = dict(funding=use_funding, fund_dir=fund_dir)
    common = dict(trend_band=trend_band, stop_atr_mult=stop_atr_mult,
                  cover_mult=cover_mult, delta_max_pct=delta_max_pct,
                  leg_fee=fee_bps / 1e4, flat_fee=flat_fee_bps / 1e4,
                  flat_slip=slip_bps / 1e4)

    def _sim(**kw):
        """Simulate, with the 1m tape attached iff this is the 1m variant.

        The tape is handed over by ENV because that is how the generated dual
        engine finds it. The variable is cleared afterwards so a later 15m run
        in the same process cannot silently inherit it.
        """
        if fill_1m:
            os.environ["NP_1M_CSV"] = one_m_path
        else:
            os.environ.pop("NP_1M_CSV", None)
        try:
            return X.simulate(bars, sym, **kw)
        finally:
            os.environ.pop("NP_1M_CSV", None)

    tr = {}
    eq = _sim(track=tr, init=init, **common, **fund_cfg)
    cp = np.asarray(tr["closed_pnl"], float)
    pf, win, n_tr = X.metrics(list(cp))
    gross = float(np.abs(cp).sum()) or 1.0
    total = float(cp.sum())
    srt = np.sort(cp)[::-1] if len(cp) else np.zeros(1)
    best5 = float(srt[:5].sum())
    best5_share = 100.0 * best5 / total if total else float("nan")
    without5 = 100.0 * (total - best5) / init

    def _slices(e, k=3):
        e = np.asarray(e, float)
        out = []
        for i in range(k):
            a, b = int(len(e) * i / k), int(len(e) * (i + 1) / k)
            out.append(100.0 * (e[b - 1] / e[a] - 1.0) if b > a and e[b - 1] > 0 else 0.0)
        return out

    sl = _slices(tr["eq_curve"])

    # Frozen-config split at 2023-01-01: the SAME run cut in two, not a re-fit.
    # This is the honest version of "OOS" for a config that was chosen on history:
    # it shows the edge is not carried by one regime, and it deliberately does NOT
    # re-optimise on the test window (that would make the number meaningless).
    split_ms = int(pd.Timestamp("2023-01-01", tz="UTC").timestamp() * 1000)
    idx = next((i for i, b in enumerate(bars) if b[0] >= split_ms), len(bars) - 1)
    ct = np.asarray(tr["closed_t"], int)
    test_mask = ct >= split_ms
    tpnl = cp[test_mask]

    def _pf(a):
        a = np.asarray(a, float)
        w, l = float(a[a > 0].sum()), float(-a[a <= 0].sum())
        if l > 0:
            return w / l
        return float("inf") if w > 0 else 0.0

    eqc = np.asarray(tr["eq_curve"], float)
    seg = eqc[idx:]
    if len(seg) > 1:
        pk = np.maximum.accumulate(seg)
        seg_mdd = float(np.max((pk - seg) / np.maximum(pk, 1e-9)) * 100.0)
    else:
        seg_mdd = 0.0
    train_ret = 100.0 * (eqc[idx - 1] / eqc[0] - 1.0) if idx > 0 else 0.0
    test_ret = 100.0 * (eqc[-1] / eqc[idx - 1] - 1.0) if idx > 0 else 0.0

    # Bootstrap of the mean per trade. Seeded and sequential ON PURPOSE: this is
    # the exact stream code/xrp_neutral_gauntlet.py used, so the artifact and the
    # gauntlet quote the same interval instead of two drifting ones.
    rng = np.random.default_rng(7)
    boot = np.array([rng.choice(cp, len(cp), replace=True).mean() for _ in range(20000)]) \
        if len(cp) > 1 else np.zeros(1)
    ci_lo, ci_hi = (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))
    boot_t = (float(cp.mean() / (cp.std(ddof=1) / np.sqrt(len(cp))))
              if len(cp) > 2 and cp.std(ddof=1) > 0 else float("nan"))
    p_le0 = float((boot <= 0).mean()) if len(cp) > 1 else 1.0

    # Neutrality, measured: average |net notional| / equity, per bar.
    e = np.asarray(tr["eq_curve"], float)
    d = np.asarray(tr["delta_curve"], float)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.abs(d) / np.where(e > 0, e, np.nan)
    avg_delta = float(np.nanmean(ratio) * 100.0)
    max_delta = float(np.nanmax(ratio) * 100.0)

    # 10x is a MARGIN claim, so it is measured here: Binance's base-tier
    # maintenance is 0.5% of gross notional, and the buffer is how far equity
    # stayed above it. A cell that breaches this is not "profitable", it is dead.
    _eqc = np.asarray(tr["eq_curve"], float)
    _gross = np.asarray(tr["gross_curve"], float)
    _maint = 0.005 * _gross
    min_buf = (float(np.min((_eqc - _maint) / np.maximum(_eqc, 1e-12)) * 100.0)
               if len(_eqc) else 0.0)
    _expo = np.asarray(tr["expo_curve"], float)
    max_exp = float(np.max(_expo)) if len(_expo) else 0.0
    bars_over = int(np.sum(_expo > leverage + 1e-9))

    # The falsification control: the SAME book with the short side switched off.
    long_eq = _sim(allow_short=False, init=init, **common, **fund_cfg) \
        if want_control else float("nan")

    # Funding coverage: a truncated history means the early bars were charged
    # nothing, and the equity is quietly wrong.
    covers, f_first, f_last, f_n = (False, 0, 0, 0)
    if funding_path:
        recs = json.load(open(funding_path, encoding="utf-8"))
        fts = [int(x["t"]) for x in recs]
        f_first, f_last, f_n = min(fts), max(fts), len(fts)
        covers = (f_first <= bars[0][0] + 8 * 3600 * 1000
                  and f_last >= bars[-1][0] - 8 * 3600 * 1000)

    # per-side and per-exit-reason tables: where the P&L actually comes from
    trades = tr.get("trades") or []
    side_rows = []
    for side, label in ((1, "long"), (-1, "short")):
        rows = [t_ for t_ in trades if t_["dir"] == side]
        pnl = np.array([t_["pnl"] for t_ in rows], float)
        w = pnl[pnl > 0]
        l = pnl[pnl <= 0]
        side_rows.append({
            "side": label, "trades": len(rows),
            "pnl": float(pnl.sum()) if len(pnl) else 0.0,
            "win_rate_pct": (100.0 * len(w) / len(pnl)) if len(pnl) else 0.0,
            "PF": (float(w.sum() / abs(l.sum())) if len(l) and l.sum() != 0
                   else (float("inf") if len(w) else 0.0)),
        })
    # Grouped from the TRADES, not from tr["reasons"]: the engine counts only
    # stop/trend_flatten/reanchor in that dict and tracks covers separately, so
    # reading it here silently dropped every cover -- 4,761 of 5,876 rows.
    by_reason = {}
    for t_ in trades:
        by_reason.setdefault(t_["reason"], []).append(t_)
    reason_rows = []
    for reason in sorted(by_reason):
        rs = by_reason[reason]
        reason_rows.append({"reason": reason, "count": len(rs),
                            "closed_pnl": float(sum(x_["pnl"] for x_ in rs)),
                            "win_rate_pct": 100.0 * sum(1 for x_ in rs if x_["pnl"] > 0) / len(rs)})

    def _f(v):
        if isinstance(v, (bool, np.bool_)):
            return bool(v)
        if isinstance(v, str):
            return v
        if isinstance(v, (int, np.integer)):
            return int(v)
        v = float(v)
        return v if np.isfinite(v) else float("nan")

    metrics = {k: _f(v) for k, v in {
        "bars": len(bars), "n_trades": n_tr,
        "return_pct": 100.0 * (eq / init - 1.0),
        "profit_factor": pf, "win_rate": win,
        "expectancy_per_trade": float(cp.mean()) if len(cp) else 0.0,
        "max_dd_pct": tr["mdd"], "fees": tr["fees"],
        "funding_paid": tr["fund"], "final_equity": eq,
        # The accounting identity, published so a reader does not have to trust
        # prose: every trade's pnl already has BOTH fees inside it (the engine
        # stores the entry fee in lot[3] and subtracts it plus the exit fee on
        # close), so equity change must equal closed P&L minus funding.
        "init_equity": init, "net_pnl_usd": eq - init,
        "closed_pnl_usd": total,
        "identity_gap_usd": (total - tr["fund"]) - (eq - init),
        "flag": "OK" if n_tr >= MIN_TRADE_FLAG else "INSUFFICIENT_SAMPLE",
        "commission_gross_pct": 100.0 * tr["fees"] / gross,
        "bh_return_pct": 100.0 * (bars[-1][4] / bars[0][4] - 1.0),
        "cost_bp_roundtrip": 2.0 * (fee_bps + slip_bps),
        "fee_bps_per_side": fee_bps, "flat_fee_bps_per_side": flat_fee_bps,
        "slippage_bps": slip_bps,
        # ── neutrality (the claim under test)
        "avg_abs_delta_pct": avg_delta, "max_abs_delta_pct": max_delta,
        "delta_cap_pct": 100.0 * delta_max_pct,
        "max_delta_at_fill_pct": tr.get("max_delta_fill_pct", 0.0),
        "delta_cap_hits": tr["delta_cap_hits"],
        "long_only_return_pct": 100.0 * (long_eq / init - 1.0) if want_control else float("nan"),
        "neutral_minus_long_pp": (100.0 * (eq - long_eq) / init) if want_control else float("nan"),
        # ── sizing / margin: 10x is a ceiling, so it is measured
        "grid_levels_per_side": int(X.GRID_LEVELS),
        "gross_capacity_usdt": init * equity_pct * 2 * int(X.GRID_LEVELS),
        "equity_pct_per_level": equity_pct,
        "leverage_cap": leverage,
        "max_gross_leverage": max_exp,
        "min_margin_buffer_pct": min_buf,
        "maint_margin_pct": 0.5,
        "bars_over_leverage": bars_over,
        # ── the gates
        "best5_share_pct": best5_share, "net_without_best5_pct": without5,
        "boot_ci_lo": ci_lo, "boot_ci_hi": ci_hi,
        "boot_t": boot_t, "boot_p_le_zero": p_le0,
        "boot_draws": 20000, "boot_seed": 7,
        "period1_pct": sl[0], "period2_pct": sl[1], "period3_pct": sl[2],
        "n_periods_green": int(sum(1 for x in sl if x > 0)),
        # ── frozen split (same run, no re-fit)
        "split_date": "2023-01-01",
        "train_return_pct": train_ret, "test_return_pct": test_ret,
        "test_n_trades": int(test_mask.sum()),
        "test_profit_factor": _pf(tpnl), "test_win_rate": (
            100.0 * float((tpnl > 0).mean()) if len(tpnl) else 0.0),
        "test_max_dd_pct": seg_mdd,
        # ── funding provenance
        "funding_attached": bool(use_funding and funding_path),
        "funding_charged": bool(use_funding),
        "funding_covers_bars": bool(covers),
        "n_funding_events": int(tr.get("n_funding_events", 0)),
        "funding_prints": int(f_n),
        # ── mechanics
        "grids_built": tr["grids"], "fills": tr["fills"], "cycles": tr["cycles"],
        "open_lots": tr["open_lots"],
        "stand_down_bars": tr["stand_down_bars"],
        "trend_band": trend_band, "stop_atr_mult": stop_atr_mult,
        "cover_mult": cover_mult,
        # ── 1m fill accounting (1m variant only): how much of the run was
        # actually resolved minute by minute, and how often the 15m convention
        # would have credited a cover the tape cannot order.
        **({"fill_timeframe": "1m",
            "bars_resolved": int(tr.get("bars_resolved", 0)),
            "bars_partial": int(tr.get("bars_partial", 0)),
            "bars_no_tape": int(tr.get("bars_no_tape", 0)),
            "minutes_used": int(tr.get("minutes_used", 0)),
            "same_minute_touched": int(tr.get("same_minute_touched", 0)),
            "same_bar_covers": int(tr.get("same_bar_covers", 0)),
            "one_m_covers": int(tr.get("one_m_covers", 0))} if fill_1m else {}),
    }.items()}

    prov = {
        "adapter": "xrpneutral1m" if fill_1m else "xrpneutral",
        # engine_version IS part of core, so the 15m branch must keep its
        # original string or every stored xrpneutral artifact stops verifying.
        "engine_version": "xrp-neutral-1m-1" if fill_1m else "xrp-neutral-1",
        "engine_file": engine_file,
        "fill_model": ("1m_resolved_on_complete_tape; same-bar fallback otherwise"
                       if fill_1m else "same_15m_bar"),
        "mode": "forward-paper-mirror",
        "deployed_bot": {
            "name": "neutral paper book (5 pairs)", "symbol": "XRPUSDT",
            "timeframe": "15m",
            "vps_dir": "/home/ubuntu/neutral-paper",
            "cron": "4,19,34,49 * * * * /home/ubuntu/neutral-paper/XRP/run.sh",
            "paper_only": True,
            "note": "the single-pair /home/ubuntu/xrp-paper-bot/ bot was retired and "
                    "deleted on 2026-11-04; this adapter is its engine, not its deploy",
        },
        "sizing": {
            "init_usdt": init, "equity_pct_per_level": equity_pct,
            "leverage_cap": leverage,
            "gross_capacity_usdt": init * leverage,
            "note": "leverage is a CEILING (init x leverage max gross), not the "
                    "average exposure; max_gross_leverage is measured from the run",
        },
        "engine_is_not": "grid_audit.simulate (that file is the validated long-grid "
                         "engine; modifying it would invalidate 300+ artifacts)",
        "neutrality": {
            "definition": "average |net notional| / equity, per bar",
            "cap": delta_max_pct * 100.0,
            "cap_enforced_at": "fill time, against contemporaneous equity",
            "falsification_control": "long_only_return_pct (same book, short side off)",
        },
        "funding": {
            "charged": bool(use_funding),
            "convention": "settlement at t charged on the first bar with open >= t, "
                          "against the NET position",
            "covers_bars": bool(covers),
            "first_print": (datetime.fromtimestamp(f_first / 1000, timezone.utc)
                            .isoformat(timespec="seconds") if f_first else None),
            "last_print": (datetime.fromtimestamp(f_last / 1000, timezone.utc)
                           .isoformat(timespec="seconds") if f_last else None),
        },
        "bootstrap": {"draws": 20000, "seed": 7, "stat": "mean per closed trade"},
    }
    tables = [{"kind": "side", **{k: _f(v) for k, v in r.items()}} for r in side_rows]
    tables += [{"kind": "exit", **{k: _f(v) for k, v in r.items()}} for r in reason_rows]
    return metrics, prov, tables


def run_q10diag(paths, params):
    """Step-zero descriptive diagnostics for the Qwen ten-card pack.

    Engine code/q10_diag.py; mode=funding|calendar|ranks selects the
    descriptive script. No trading, no costs, no strategy returns: pure
    measurements over the funding JSONs and 1h klines with the pre-declared
    kill bars from results/qwen_pack10_grade.md carried as metrics. The
    symbol key declares the file set (FUNDING / CALENDAR / RANKS) and the
    dispatcher refuses any mismatch so no unhashed file is ever read.
    """
    D = _load_module(os.path.join(CODE, "q10_diag.py"), "q10_diag")
    mode = str(params.get("mode", "")).lower()
    if mode not in ("funding", "calendar", "ranks"):
        raise ValueError("q10diag params: mode must be funding|calendar|ranks")
    if mode == "funding":
        exp = (sorted(f"{s}_funding.json" for s in D.FUND_SYMS)
               + sorted(f"{s}_1h.csv" for s in D.FUND_SYMS))
    elif mode == "calendar":
        exp = (sorted(f"{s}_1h.csv" for s in D.FUND_SYMS)
               + sorted(f"{s}_funding.json" for s in D.FUND_SYMS))
    else:
        exp = sorted(f"{s}_1h.csv" for s in D.TEN_SYMS)
    got = sorted(os.path.basename(p) for p in paths)
    if got != sorted(exp):
        raise ValueError(f"q10diag mode={mode}: input file set mismatch: "
                         f"{got} != {sorted(exp)}")
    metrics, prov, tables = D.run(mode, paths)
    prov = dict(prov)
    prov["adapter"] = "q10diag"
    prov["engine_version"] = "q10diag-1"
    return metrics, prov, tables


_Q10_MAJORS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")
_Q10_TEN = _Q10_MAJORS + ("BNBUSDT", "LINKUSDT", "ADAUSDT", "DOGEUSDT",
                          "AVAXUSDT", "NEARUSDT")


def _q10_inputs(sym: str) -> list:
    """The declared per-card input file set (engine-side EXPECTED_FILES
    mirrors this exactly; any mismatch becomes a run refusal, never a guess)."""
    kl = "binance_klines_1h"
    fd = "binance_funding"
    kl_syms = ("BTCUSDT", "ETHUSDT") if sym == "CARD3" else \
        (_Q10_TEN if sym in ("CARD2", "CARD10") else _Q10_MAJORS)
    fd_syms = ("BTCUSDT", "ETHUSDT") if sym == "CARD3" else _Q10_MAJORS
    return [os.path.join(DATA, kl, f"{s}_1h.csv") for s in kl_syms] + \
        [os.path.join(DATA, fd, f"{s}_funding.json") for s in fd_syms]


def run_q10(paths, params):
    """The six surviving declared Qwen cells after Step zero (cards one,
    two, three, four, nine, ten), engine code/q10_engine.py shared with
    code/q10_diag.py (both hashed). `card` arrives from --symbol via the
    card_from_symbol flag; the card's declared file set is enforced twice
    (adapter + engine) so no unhashed file is ever read. The known-answer
    audit code/_q10_audit.py (results/q10_engine_audit.txt) must be ALL
    PASS on the engine bytes before and after these runs (REGLA 0)."""
    E = _load_module(os.path.join(CODE, "q10_engine.py"), "q10_engine")
    p = dict(params)
    card = str(p.pop("card", "")).strip().upper()
    if not card.startswith("CARD"):
        raise ValueError("q10 run needs the card symbol (CARD1..CARD10)")
    if sorted(os.path.basename(x) for x in paths) != \
       sorted(os.path.basename(x) for x in _q10_inputs(card)):
        raise ValueError(f"q10 {card}: input file set mismatch")
    metrics, prov, tables = E.run(card, paths)
    prov = dict(prov)
    prov["adapter"] = "q10"
    prov["engine_version"] = E.ENGINE_VERSION
    prov["audit"] = ("code/_q10_audit.py ALL PASS on these engine bytes "
                     "(results/q10_engine_audit.txt)")
    return metrics, prov, tables


def run_fingrad(paths, params):
    """Fingrad HMA·AO·ADX (Pine v6) port — code/fingrad_engine.py, known-answer
    audited by code/_fingrad_audit.py before any real-data run."""
    sys.path.insert(0, CODE)
    import importlib
    m = importlib.import_module("fingrad_engine")
    out = m.run_symbol(paths, dict(params))
    return (out["metrics"],
            {"adapter": "fingrad", "engine_version": "fingrad-1"},
            out["tables"])


def run_prompts100(paths, params):
    """The 5 OOS survivors of the prompts-100 screen (backtest_prompts100,
    2026-10-29) through their frozen port code/prompts100_engine.py: #28
    Donchian breakout BTC 1h, #44 168-bar breakout BTC 1h, #60 Keltner+RSI
    HYPE 1h, #71 Hour-of-day filter JUP 1h, #73 Sunday-to-Monday reversion
    ETH 1h. Conventions of the source screen (signal close / fill next open,
    stop wins ties, 1% risk per ATR stop, 70/30 IS-OOS, 11 bps RT). One run
    per survivor: --set id=28|44|60|71|73; the engine refuses any other
    symbol than the survivor's own."""
    m = _load_module(os.path.join(CODE, "prompts100_engine.py"), "prompts100_engine")
    return m.run(paths, dict(params))


def run_top10(paths, params):
    """The TOP10 shortlist of the prompts-100 screen (TOP10_ESTRATEGIAS.md,
    2026-11-01) through their frozen port code/top10_engine.py: the five
    prompts100 survivors (#28 #44 #60 #71 #73) plus #56 Donchian chandelier
    JUP 1h, #95 price-funding divergence SUI 1h (funding charged), #26 EMA
    cross ETH 1h, #34 regression slope SOL 1h, #59 range expansion SOL 1h.
    Conventions of the source screen (signal close / fill next open, exit
    signal executed at the open before the stop check, gap-through stops,
    1% risk per trade, 70/30 IS-OOS, 11 bps RT). One run per strategy:
    --set id=26|28|34|44|56|59|60|71|73|95; the engine refuses any other
    symbol than the strategy's own. Audits: code/_top10_audit.py (19/19
    known answers) and code/_top10_parity.py (110/110: trade-level identity
    with the source engine on the same bytes + results_100.csv reproduced
    + truncation invariance)."""
    m = _load_module(os.path.join(CODE, "top10_engine.py"), "top10_engine")
    return m.run(paths, dict(params))


def _top10_inputs(tf, sym):
    import glob
    d, suf = TF_DIR[tf]
    native = os.path.join(d, f"{sym}_{suf}.csv")
    if os.path.exists(native):
        files = [native]
    else:
        dt, st = TF_TAKER[tf]
        files = [os.path.join(dt, f"{sym}_{st}.csv")]
    # appended API tail files (new data files only; existing files untouched)
    files += sorted(glob.glob(os.path.join(d, f"{sym}_{suf}_tail_*.csv")))
    # the one funding strategy (#95, SUIUSDT) needs the settlement history;
    # funding_covers_bars is measured inside the artifact
    if sym.upper() == "SUIUSDT":
        files.append(os.path.join(DATA, "binance_funding", "SUIUSDT_funding.json"))
    return files


def _bookreplay_inputs(tf, sym):
    """15m klines CSV + the REAL aggTrades daily CSVs (official Binance bulk
    archive, data/aggtrades/<SYM>/, fetched by code/fetch_aggtrades.py with a
    sha256 manifest). The engine asserts day contiguity and refuses to run on
    a gapped window."""
    files = [os.path.join(TF_DIR["15m"][0], f"{sym}_15m.csv")]
    files += sorted(glob.glob(os.path.join(DATA, "aggtrades", sym,
                                           f"{sym}-aggTrades-*.csv")))
    return files


def run_bookreplay(paths, params):
    """Fill-resolution replay (code/bookreplay_engine.py, 2026-11-01).

    The SAME resting-maker grid resolved two ways on the SAME window —
    MODEL TRADES on real executed aggTrades (official archive, hashed) vs
    MODEL 15M on the bar convention that credits same-bar covers — so the only
    difference is fill resolution. This is the forward record the repo
    fill-model rule demands after the XRP neutral kill (15m OHLC credited a
    cover whenever the same bar's high reached the cover level; the 1m audit
    measured 100% of the book's trades were such same-bar round trips).

    The symbol comes from the klines CSV filename (harness convention).
    Params (all optional): levels, spacing_pct, notional_usdt, equity0,
    maker_fee_bps, leverage_cap. Funding is excluded from BOTH models on
    purpose: the comparison isolates resolution, not carry."""
    B = _load_fresh(os.path.join(CODE, "bookreplay_engine.py"), "bookreplay_engine_run")
    p = dict(params)
    csvs = [x for x in paths
            if str(x).lower().endswith(".csv") and "aggtrades" not in str(x).lower()]
    sym = os.path.basename(csvs[0]).split("_")[0].upper()
    p.setdefault("symbol", sym)
    return B.run(paths, p)


def run_xsf(paths, params):
    """Cross-sectional factor books, Category A (code/xs_factor_engine.py,
    2026-11-02). Three rank-rotation books on the 1h universe-14 -- LOWVOL
    (336h realized vol: long low / short high), SKEW (720h skewness: long low
    / short high), AUTOCORR (336h lag-1 AC: long persistent / short churn) --
    selected with --symbol LOWVOL|SKEW|AUTOCORR (card_from_symbol, like q10).
    Decisions on the close of rebalance bars (every `reb`, default 336),
    execution at the next open, 11 bps RT (fee 5.0 + slip 0.5 per side),
    hysteresis bands (enter rank<=k, hold while rank<=2k), zero-cost control
    and gate battery inside the artifact. Funding NOT charged: 7 of the 14
    names have no funding file on disk (declared in provenance)."""
    E = _load_fresh(os.path.join(CODE, "xs_factor_engine.py"), "xs_factor_engine_run")
    return E.run(paths, dict(params))


def run_xsb(paths, params):
    """Cross-sectional relative-value books, Category B 
    (code/xs_factor_b_engine.py, 2026-11-02). Two cards on the 1h 
    universe-14, selected with --symbol VOLCOMP|DDRELAY 
    (card_from_symbol). VOLCOMP: z-score of relative vol 
    (vol/median-vol) with a drift gate on ROC(168h) for entries; 
    DDRELAY: event-conditional drawdown relay, active while the 
    cross-sectional median 30d return is below --set trig (default 
    -0.20), fixed k=2, weekly decisions. Both reuse the Category A 
    machinery untouched (xs_factor_engine.py is hash-pinned by the 
    nine Category A artifacts), so BOTH engine files are hashed into 
    the run_id."""
    E = _load_fresh(os.path.join(CODE, "xs_factor_b_engine.py"), "xs_factor_b_engine_run")
    return E.run(paths, dict(params))


def run_xsc(paths, params):
    """Cross-sectional funding-filtered books, Category C 
    (code/xs_factor_c_engine.py, 2026-11-02). Two cards on the 
    SEVEN funding-covered names, selected with --symbol 
    FUNDGATE|FUNDTAIL (card_from_symbol). FUNDGATE: ROC(336h) 
    top-2/bottom-2 with a funding-sign entry gate (long only if it 
    receives, short only if it receives). FUNDTAIL: low-vol book 
    with an extreme-funding exclusion (--set cap, default 0.0005 
    per 8h). FUNDING IS CHARGED here at the real settlement 
    instants (raw rates; JUP/HYPE bill 4h cadence), unlike A/B 
    where it was declared uncharged. The adapter hashes the C 
    engine, the pinned A engine (whose machinery C imports) and 
    all fourteen data files into the run_id."""
    E = _load_fresh(os.path.join(CODE, "xs_factor_c_engine.py"), "xs_factor_c_engine_run")
    return E.run(paths, dict(params))


def _prompts100_inputs(tf, sym):
    d, suf = TF_DIR[tf]
    native = os.path.join(d, f"{sym}_{suf}.csv")
    if os.path.exists(native):
        files = [native]
    else:  # JUPUSDT exists only in the taker cache (same fallback as smqe)
        dt, st = TF_TAKER[tf]
        files = [os.path.join(dt, f"{sym}_{st}.csv")]
    import glob
    # appended API tail files (new data files only; existing files untouched)
    files += sorted(glob.glob(os.path.join(d, f"{sym}_{suf}_tail_*.csv")))
    return files


def run_smqe(paths, params):
    """SMQE v2 strategy (Pine v6 attachment, source of record copied
    byte-identical to code/smqe_v2_strategy.pine) — port in
    code/smqe_engine.py, known-answer audited by code/_smqe_audit.py
    (40/40 PASS, results/smqe_audit_known_answers.txt) before any real-data
    run. Entry/flip fills at the signal bar's close (process_orders_on_close),
    bracket TP1-50%/TP2/stop, min-stop floor, constant-rate funding ledger,
    daily breaker, equity-DD killswitch. Params: cost_mode (repo|pine|zero),
    sim_start, sim_end. The Pine's confluence gates ship OFF, so the SMC and
    MA-OB engines are display-only and are not ported (declared in the engine
    docstring)."""
    sys.path.insert(0, CODE)
    import importlib
    m = importlib.import_module("smqe_engine")
    out = m.run_symbol(paths, dict(params))
    return (out["metrics"],
            {"adapter": "smqe", "engine_version": "smqe-1"},
            out["tables"])


def run_xrpneutral_1m(paths, params):
    """The same neutral book, with fills resolved on the 1m tape.

    The engine is `code/xrp_neutral_engine_paper_1m.py`, GENERATED by
    `code/_neutral_1m_build.py` from `code/xrp_neutral_engine_paper.py` (the
    byte-identical copy of what the VPS runs). A bar is resolved minute by
    minute only when its tape is COMPLETE (>= 15 distinct minutes); every other
    bar keeps the 15m same-bar model byte for byte, which is why a slice with no
    tape reproduces the 15m engine exactly instead of approximately.

    Why this exists at all: the 15m convention credits a cover whenever the same
    bar's high reaches the cover level. On this book that is not a rare edge
    case, it is the book (100% of the retired XRP bot's trades were same-bar
    round trips). The 1m number is the one that resolves fills in time order.

    `code/_neutral_1m_audit.py` proves the two engines agree everywhere the tape
    is absent, and reproduces this run's numbers independently.
    """
    p = dict(params)
    p["fill_1m"] = True
    p["_engine_file"] = "xrp_neutral_engine_paper_1m.py"
    return run_xrpneutral(paths, p)


ADAPTERS = {
    "smqe": {
        "sources": [os.path.join(CODE, "smqe_engine.py"),
                    os.path.join(CODE, "smqe_v2_strategy.pine")],
        "version": "smqe-1",
        # Harness-native klines first (long history, 13+6 symbols); the taker
        # dirs are the FALLBACK because JUPUSDT exists only there. At 5m the
        # taker dir is the PRIMARY: the native 5m dir holds ~2-month stubs
        # while the taker files carry two years (2024-10..2026-10). The OHLCV
        # columns are identical and the engine reads the first six fields
        # positionally, so the extra taker columns are ignored.
        "inputs": lambda tf, sym: [
            os.path.join(TF_TAKER[tf][0], f"{sym}_{TF_TAKER[tf][1]}.csv")
            if tf == "5m" or not os.path.exists(
                os.path.join(TF_DIR[tf][0], f"{sym}_{TF_DIR[tf][1]}.csv"))
            else os.path.join(TF_DIR[tf][0], f"{sym}_{TF_DIR[tf][1]}.csv"),
        ],
        "run": run_smqe, "matrix": True, "needs_tf": True,
        # 1m stays out of the sweep by design: the session-VWAP + divergence
        # core is out of its design range there, and every 1m campaign in
        # this repo has been ruin once costs are charged.
        "matrix_dirs": {"1h": TF_DIR["1h"], "15m": TF_DIR["15m"],
                        "5m": TF_TAKER["5m"]},
    },
    "fingrad": {
        "sources": [os.path.join(CODE, "fingrad_engine.py")],
        "version": "fingrad-1",
        "inputs": lambda tf, sym: [
            os.path.join(TF_DIR[tf][0], f"{sym}_{TF_DIR[tf][1]}.csv"),
            *([os.path.join(DATA, "binance_funding", f"{sym}_funding.json")]
              if os.path.exists(os.path.join(DATA, "binance_funding",
                                             f"{sym}_funding.json")) else []),
        ],
        "run": run_fingrad, "matrix": True, "needs_tf": True,
    },
    "q10diag": {
        "sources": [os.path.join(CODE, "q10_diag.py")],
        "version": "q10diag-1",
        "inputs": lambda tf, sym: (
            [os.path.join(DATA, "binance_funding", f"{s}_funding.json") for s in
             ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")]
            + [os.path.join(DATA, "binance_klines_1h", f"{s}_1h.csv") for s in
               ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")]
            if sym == "FUNDING" else
            [os.path.join(DATA, "binance_klines_1h", f"{s}_1h.csv") for s in
             ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")]
            + [os.path.join(DATA, "binance_funding", f"{s}_funding.json") for s in
               ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")]
            if sym == "CALENDAR" else
            [os.path.join(DATA, "binance_klines_1h", f"{s}_1h.csv") for s in
             ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "LINKUSDT",
              "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "NEARUSDT")]),
        "run": run_q10diag, "matrix": False, "needs_tf": False,
    },
    "xrpneutral": {
        "sources": [os.path.join(CODE, "xrp_neutral_engine.py")],
        "version": "xrp-neutral-1",
        "inputs": lambda tf, sym: [
            os.path.join(TF_DIR["15m"][0], f"{sym}_15m.csv"),
            os.path.join(DATA, "binance_funding", f"{sym}_funding.json"),
        ],
        "run": run_xrpneutral, "matrix": False, "needs_tf": True,
    },
    # The SAME book with fills resolved on the 1m tape. A separate adapter, not a
    # flag on the one above: the tape is an INPUT and inputs are hashed into
    # run_id, so adding it there would re-key every stored xrpneutral artifact,
    # including the two that record the validated v1/v2 books.
    "xrpneutral1m": {
        "sources": [os.path.join(CODE, "xrp_neutral_engine_paper_1m.py"),
                    os.path.join(CODE, "xrp_neutral_engine_paper.py"),
                    os.path.join(CODE, "_neutral_1m_build.py")],
        "version": "xrp-neutral-1m-1",
        "inputs": lambda tf, sym: [
            os.path.join(TF_DIR["15m"][0], f"{sym}_15m.csv"),
            os.path.join(DATA, "binance_funding", f"{sym}_funding.json"),
            os.path.join(DATA, "binance_klines_1m", f"{sym}_1m.csv"),
        ],
        "run": run_xrpneutral_1m, "matrix": False, "needs_tf": True,
    },
    "cbpack": {
        "sources": [os.path.join(CODE, "cbpack_engine.py")],
        "version": "cbpack-1",
        "inputs": lambda tf, sym: [
            os.path.join(TF_TAKER[tf][0], f"{sym}_{TF_TAKER[tf][1]}.csv"),
            *([os.path.join(DATA, "binance_funding", f"{sym}_funding.json")]
              if os.path.exists(os.path.join(DATA, "binance_funding", f"{sym}_funding.json")) else []),
        ],
        "run": run_cbpack, "matrix": True, "needs_tf": True, "matrix_dirs": TF_TAKER,
    },
    "cbpackf": {
        "sources": [os.path.join(CODE, "cbpack_funding_engine.py")],
        "version": "cbpack-funding-1",
        "inputs": lambda tf, sym: [
            os.path.join(TF_TAKER[tf][0], f"{sym}_{TF_TAKER[tf][1]}.csv"),
            *([os.path.join(DATA, "binance_funding", f"{sym}_funding.json")]
              if os.path.exists(os.path.join(DATA, "binance_funding", f"{sym}_funding.json")) else []),
        ],
        "run": run_cbpackf, "matrix": True, "needs_tf": True, "matrix_dirs": TF_TAKER,
    },
    "sax": {
        "sources": [SAX_ENGINE],
        "version": "3.0.0",
        "inputs": lambda tf, sym: [os.path.join(TF_DIR[tf][0], f"{sym}_{TF_DIR[tf][1]}.csv")],
        "run": run_sax, "matrix": True,
    },
    "cvrmd": {
        "sources": [os.path.join(CODE, "cvrmd_backtest.py")],
        "version": "cvrmd",
        "inputs": lambda tf, sym: [os.path.join(TF_DIR[tf][0], f"{sym}_{TF_DIR[tf][1]}.csv")],
        "run": run_cvrmd, "matrix": True,
    },
    "botstrat": {
        "sources": [os.path.join(CODE, "botstrat_backtest.py")],
        "version": "botstrat",
        "inputs": lambda tf, sym: [os.path.join(TF_DIR[tf][0], f"{sym}_{TF_DIR[tf][1]}.csv")],
        "run": run_botstrat, "matrix": True,
    },
    "ffs": {
        "sources": [os.path.join(CODE, "ffs_engine.py"), os.path.join(CODE, "ffs_engine2.py")],
        "version": "ffs",
        "inputs": lambda tf, sym: [os.path.join(TF_DIR[tf][0], f"{sym}_{TF_DIR[tf][1]}.csv")],
        "run": run_ffs, "matrix": True,
    },
    "mp20": {
        "sources": [os.path.join(CODE, "mp20_report_ports.py")],
        "version": "mp20",
        "inputs": lambda tf, sym: [os.path.join(DATA, "binance_klines_1h", f"{s}_1h.csv")
                                   for s in ("BTCUSDT", "ETHUSDT", "SOLUSDT",
                                             "AVAXUSDT", "LINKUSDT")],
        "run": run_mp20, "matrix": False,
    },
    "mps20": {
        "sources": [os.path.join(CODE, "claude_bot_1", "engine_core.py"),
                    os.path.join(CODE, "claude_bot_1", "strategies.py")],
        "version": "mps20-1",
        "inputs": lambda tf, sym: [os.path.join(DATA, "binance_klines_1h", f"{s}_1h.csv")
                                   for s in ("BTCUSDT", "ETHUSDT", "SOLUSDT",
                                             "AVAXUSDT", "LINKUSDT", "XRPUSDT")],
        "run": run_mps20, "matrix": False,
    },
    "mpv3": {
        "sources": [os.path.join(CODE, "mpv3_engine.py"),
                    os.path.join(CODE, "claude_mp20_v3", "strategies.py")],
        "version": "mpv3-1",
        "inputs": lambda tf, sym: [os.path.join(DATA, "binance_klines_1h", f"{s}_1h.csv")
                                   for s in ("AVAXUSDT", "BTCUSDT", "ETHUSDT", "LINKUSDT", "SOLUSDT")],
        "run": run_mpv3, "matrix": False, "needs_tf": False,
    },
    "pack50": {
        "sources": [os.path.join(CODE, "pack50_engine.py"),
                    os.path.join(CODE, "pack50_core.py"),
                    os.path.join(CODE, "pack50_strats.py")],
        "version": "pack50-1",
        "inputs": _pack50_inputs,
        "run": run_pack50, "matrix": False, "needs_tf": False,
    },
    "pack50b": {
        "sources": [os.path.join(CODE, "pack50b_engine.py"),
                    os.path.join(CODE, "pack50_core.py"),
                    os.path.join(CODE, "pack50b_strats.py")],
        "version": "pack50b-1",
        "inputs": _pack50b_inputs,
        "run": run_pack50b, "matrix": False, "needs_tf": False,
    },
    "gatecal": {
        "sources": [os.path.join(CODE, "gatecal_engine.py"),
                    os.path.join(CODE, "gate2.py"),
                    os.path.join(CODE, "pack50_core.py"),
                    os.path.join(CODE, "_gates_v2.py")],
        "version": "gatecal-1",
        "inputs": _gatecal_inputs,
        "run": run_gatecal, "matrix": False, "needs_tf": False,
    },
    "pack50c": {
        "sources": [os.path.join(CODE, "pack50c_engine.py"),
                    os.path.join(CODE, "pack50_core.py"),
                    os.path.join(CODE, "pack50b_engine.py"),
                    os.path.join(CODE, "pack50c_strats.py"),
                    os.path.join(CODE, "gate2.py")],
        "version": "pack50c-1",
        "inputs": _pack50c_inputs,
        "run": run_pack50c, "matrix": False, "needs_tf": False,
    },
    "pack100": {
        "sources": [os.path.join(CODE, "pack100_engine.py"),
                    os.path.join(CODE, "pack100_strats.py"),
                    os.path.join(CODE, "pack100_strats2.py"),
                    os.path.join(CODE, "pack100_strats3.py"),
                    os.path.join(CODE, "pack50_core.py"),
                    os.path.join(CODE, "pack50b_engine.py"),
                    os.path.join(CODE, "pack50b_strats.py"),
                    os.path.join(CODE, "pack50d_engine.py"),
                    os.path.join(CODE, "pack50d_strats.py"),
                    os.path.join(CODE, "gate2.py")],
        "version": "pack100-1",
        "inputs": _pack100_inputs,
        "run": run_pack100, "matrix": False, "needs_tf": False,
    },
    "qs": {
        "sources": [os.path.join(CODE, "qs_engine.py"),
                    os.path.join(CODE, "qs_strats.py"),
                    os.path.join(CODE, "qs_run.py")],
        "version": "qs-1",
        "inputs": _qs_inputs,
        "run": run_qs, "matrix": False, "needs_tf": True,
    },
    "qsf": {
        "sources": [os.path.join(CODE, "qs_engine.py"),
                    os.path.join(CODE, "qs_strats.py"),
                    os.path.join(CODE, "qs_flow_strats.py"),
                    os.path.join(CODE, "qs_run.py")],
        "version": "qsf-1",
        "inputs": _qsf_inputs,
        "run": run_qsf, "matrix": False, "needs_tf": True,
    },
    "qsb": {
        "sources": [os.path.join(CODE, "qs_engine.py"),
                    os.path.join(CODE, "qs_strats.py"),
                    os.path.join(CODE, "qs_b_strats.py"),
                    os.path.join(CODE, "qs_run.py"),
                    os.path.join(CODE, "qs_pair_run.py"),
                    os.path.join(CODE, "pack50_core.py")],
        "version": "qsb-1",
        "inputs": _qsb_inputs,
        "run": run_qsb, "matrix": False, "needs_tf": True,
    },
    "qsc": {
        "sources": [os.path.join(CODE, "qs_engine.py"),
                    os.path.join(CODE, "qs_strats.py"),
                    os.path.join(CODE, "qs_c_strats.py"),
                    os.path.join(CODE, "qs_run.py")],
        "version": "qsc-1",
        "inputs": _qsc_inputs,
        "run": run_qsc, "matrix": False, "needs_tf": True,
    },
    "qsd": {
        "sources": [os.path.join(CODE, "qs_engine.py"),
                    os.path.join(CODE, "qs_strats.py"),
                    os.path.join(CODE, "qs_d_strats.py"),
                    os.path.join(CODE, "qs_run.py")],
        "version": "qsd-1",
        "inputs": _qsd_inputs,
        "run": run_qsd, "matrix": False, "needs_tf": True,
    },
    "pack50d": {
        "sources": [os.path.join(CODE, "pack50d_engine.py"),
                    os.path.join(CODE, "pack50_core.py"),
                    os.path.join(CODE, "pack50b_engine.py"),
                    os.path.join(CODE, "pack50d_strats.py"),
                    os.path.join(CODE, "gate2.py")],
        "version": "pack50d-1",
        "inputs": _pack50d_inputs,
        "run": run_pack50d, "matrix": False, "needs_tf": False,
    },
    "gate2": {
        "sources": [os.path.join(CODE, "gate2_engine.py"),
                    os.path.join(CODE, "gate2.py"),
                    os.path.join(CODE, "pack50_core.py"),
                    os.path.join(CODE, "pack50b_engine.py"),
                    os.path.join(CODE, "pack50b_strats.py")],
        "version": "gate2-1",
        "inputs": _pack50b_inputs,
        "run": run_gate2, "matrix": False, "needs_tf": False,
    },
    "cand7": {
        "sources": [os.path.join(CODE, "cand7_engine.py"),
                    os.path.join(CODE, "cand7_core.py"),
                    os.path.join(CODE, "cand7_strats.py"),
                    os.path.join(CODE, "gate2.py")],
        "version": "cand7-1",
        "inputs": _cand7_inputs,
        "run": run_cand7, "matrix": False, "needs_tf": False,
    },
    "rsimr": {
        "sources": [os.path.join(CODE, "rsi_mr_engine.py")],
        "version": "rsi-mr-1",
        "inputs": lambda tf, sym: [os.path.join(DATA, "binance_klines_1h", f"{sym}_1h.csv")],
        "run": run_rsimr, "matrix": False, "needs_tf": False,
    },
    "eqpack": {
        "sources": [os.path.join(CODE, "cbpack_engine.py")],
        "version": "cbpack-1-eq",
        "inputs": lambda tf, sym: [os.path.join(DATA, "alpaca_1d", f"{sym}_1d.csv")],
        "run": run_eqpack, "matrix": False, "needs_tf": False,
    },
    "prompts100": {
        "sources": [os.path.join(CODE, "prompts100_engine.py")],
        "version": "prompts100-1",
        "inputs": _prompts100_inputs,
        "run": run_prompts100, "matrix": False, "needs_tf": True,
    },
    "top10": {
        "sources": [os.path.join(CODE, "top10_engine.py")],
        "version": "top10-1",
        "inputs": _top10_inputs,
        "run": run_top10, "matrix": False, "needs_tf": True,
    },
    "cbot": {
        "sources": [os.path.join(CODE, "cbot", f) for f in
                    ("__init__.py", "backtest.py", "config.py", "data.py", "features.py",
                     "model.py", "report.py", "strategies.py", "suite.py")],
        "version": "cbot-1",
        "inputs": lambda tf, sym: [os.path.join(TF_TAKER[tf][0], f"{sym}_{TF_TAKER[tf][1]}.csv")],
        "run": run_cbot, "matrix": True, "needs_tf": True, "matrix_dirs": TF_TAKER,
    },
    "emaadx": {
        "sources": [os.path.join(CODE, "emaadx_engine.py")],
        "version": "emaadx-1",
        "inputs": lambda tf, sym: [os.path.join(TF_DIR[tf][0], f"{sym}_{TF_DIR[tf][1]}.csv")],
        "run": run_emaadx, "matrix": True,
    },
    "dspack": {
        "sources": [os.path.join(CODE, "deepseek_pack.py"),
                    os.path.join(CODE, "dspack_engine.py")],
        "version": "dspack-1",
        "inputs": lambda tf, sym: (
            [os.path.join(DATA, "binance_klines_1h", f"{s}_1h.csv")
             for s in ("ADAUSDT", "AVAXUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT",
                       "ETHUSDT", "HYPEUSDT", "LINKUSDT", "NEARUSDT", "SOLUSDT",
                       "SPXUSDT", "SUIUSDT", "XRPUSDT")]
            if sym == "PORTFOLIO" else
            [os.path.join(DATA, "binance_klines_1h", f"{sym}_1h.csv")]),
        "run": run_dspack, "matrix": False, "needs_tf": True,
    },
    "dspack2": {
        "sources": [os.path.join(CODE, "deepseek_pack2.py"),
                    os.path.join(CODE, "dspack_engine.py"),
                    os.path.join(CODE, "dspack2_engine.py")],
        "version": "dspack2-1",
        "inputs": lambda tf, sym: (
            [os.path.join(DATA, "binance_klines_1h", f"{s}_1h.csv")
             for s in ("BTCUSDT", "ETHUSDT")]
            if sym == "PAIRS_BTC_ETH" else
            [os.path.join(DATA, "binance_klines_1h", f"{sym}_1h.csv")]),
        "run": run_dspack2, "matrix": True, "needs_tf": True,
    },
    "hmaaoadx": {
        "sources": [os.path.join(CODE, "fingrad_hma_ao_adx_strategy.pine"),
                    os.path.join(CODE, "emaadx_engine.py"),
                    os.path.join(CODE, "dspack_engine.py"),
                    os.path.join(CODE, "hmaaoadx_engine.py")],
        "version": "hmaaoadx-1",
        "inputs": lambda tf, sym: [os.path.join(TF_DIR[tf][0],
                                               f"{sym}_{TF_DIR[tf][1]}.csv")],
        "run": run_hmaaoadx, "matrix": True, "needs_tf": True,
        "matrix_dirs": {"1h": TF_DIR["1h"]},
    },
    "q10": {
        "sources": [os.path.join(CODE, "q10_engine.py"),
                    os.path.join(CODE, "q10_diag.py")],
        "version": "q10-engine-1",
        "inputs": lambda tf, sym: _q10_inputs(sym),
        "run": run_q10, "matrix": False, "needs_tf": False,
        "card_from_symbol": True,
    },
    "bookreplay": {
        # fill-resolution replay: the same resting-maker grid resolved on REAL
        # executed aggTrades (official Binance bulk archive, hashed) and on the
        # 15m bar convention, so the only difference is resolution. The
        # engine refuses a gapped trade window; fetch with fetch_aggtrades.py.
        "sources": [os.path.join(CODE, "bookreplay_engine.py")],
        "version": "bookreplay-1",
        "inputs": _bookreplay_inputs,
        "run": run_bookreplay, "matrix": False, "needs_tf": False,
    },
    "xsf": {
        # Cross-sectional factor books (Category A, 2026-11-02): LOWVOL /
        # SKEW / AUTOCORR rank-rotation on the 1h universe-14 (ADA ARB AVAX
        # BNB BTC DOGE ETH HYPE JUP LINK NEAR SOL SUI XRP). The card comes
        # from --symbol (card_from_symbol, like q10); params: lb (lookback,
        # default per card: 336/720/336), reb (default 336), fee_bps
        # (default 5.0), slippage_bps (default 0.5). Symbols drop out of
        # eligibility when their data ends (HYPE main file ends early; the
        # tail file is NOT spliced in) -- declared, no survivorship patch.
        "sources": [os.path.join(CODE, "xs_factor_engine.py")],
        "version": "xsf-1",
        "inputs": lambda tf, sym: [
            os.path.join(DATA, "binance_klines_1h", f"{s}_1h.csv") for s in
            ("ADAUSDT", "ARBUSDT", "AVAXUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT",
             "ETHUSDT", "HYPEUSDT", "JUPUSDT", "LINKUSDT", "NEARUSDT", "SOLUSDT",
             "SUIUSDT", "XRPUSDT")],
        "run": run_xsf, "matrix": False, "needs_tf": False,
        "card_from_symbol": True,
    },
    "xsb": {
        # Cross-sectional relative-value books (Category B, 2026-11-02):
        # VOLCOMP (relative-vol compression z-score + ROC drift gate) and
        # DDRELAY (event-conditional relative-drawdown relay, trigger
        # --set trig, default -0.20). Card from --symbol (card_from_symbol).
        # Sources include xs_factor_engine.py because the B engine imports
        # its machinery: both files are pinned by the run_id.
        "sources": [os.path.join(CODE, "xs_factor_b_engine.py"),
                    os.path.join(CODE, "xs_factor_engine.py")],
        "version": "xsb-1",
        "inputs": lambda tf, sym: [
            os.path.join(DATA, "binance_klines_1h", f"{s}_1h.csv") for s in
            ("ADAUSDT", "ARBUSDT", "AVAXUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT",
             "ETHUSDT", "HYPEUSDT", "JUPUSDT", "LINKUSDT", "NEARUSDT", "SOLUSDT",
             "SUIUSDT", "XRPUSDT")],
        "run": run_xsb, "matrix": False, "needs_tf": False,
        "card_from_symbol": True,
    },
    "xsc": {
        # Cross-sectional funding-filtered books (Category C, 2026-11-02):
        # FUNDGATE (ROC rank + funding-sign entry gate) and FUNDTAIL (low-vol
        # rank + extreme-funding exclusion, --set cap). FUNDING IS CHARGED at
        # the real settlement instants (raw file rates; JUP/HYPE 4h cadence).
        # Sources include xs_factor_engine.py (pinned by Category A) because
        # the C engine imports its machinery.
        "sources": [os.path.join(CODE, "xs_factor_c_engine.py"),
                    os.path.join(CODE, "xs_factor_engine.py")],
        "version": "xsc-1",
        "inputs": lambda tf, sym: (
            [os.path.join(DATA, "binance_klines_1h", f"{s}_1h.csv") for s in
             ("BTCUSDT", "ETHUSDT", "HYPEUSDT", "JUPUSDT", "SOLUSDT", "SUIUSDT",
              "XRPUSDT")]
            + [os.path.join(DATA, "binance_funding", f"{s}_funding.json") for s in
               ("BTCUSDT", "ETHUSDT", "HYPEUSDT", "JUPUSDT", "SOLUSDT", "SUIUSDT",
                "XRPUSDT")]),
        "run": run_xsc, "matrix": False, "needs_tf": False,
        "card_from_symbol": True,
    },
}


# ══════════════════════════════════════════════ artifact
def make_artifact(strategy: str, tf: str, symbol: str, params: dict) -> dict:
    a = ADAPTERS[strategy]
    in_paths = a["inputs"](tf, symbol)
    inputs = []
    for p in in_paths:
        if not os.path.exists(p):
            raise FileNotFoundError(p)
        inputs.append(_read_input(p))

    # adapters that need the timeframe for internal timing get it injected; the
    # run_id uses the CLI params only, so an injected key never changes an id.
    # The q10 card key is DIFFERENT by design: two cards can share one input
    # file set (CARD1/CARD4/CARD9 all read the majors), so the card MUST be
    # part of core, else those artifacts collide on one id.
    run_params = {**params, "tf": tf} if a.get("needs_tf") else dict(params)
    if a.get("card_from_symbol"):
        params = {**params, "card": symbol}
        run_params = dict(params)
    metrics, prov, tables = a["run"](in_paths, run_params)

    prov = dict(prov)
    prov["engine_files"] = [os.path.basename(s) for s in a["sources"]]
    if os.path.exists(a["sources"][0]) and all(os.path.exists(s) for s in a["sources"]):
        prov["engine_sha256"] = _sha256_engine(a["sources"])
    else:
        prov["engine_sha256"] = SAX_ENGINE_SHA
    prov["engine_version"] = prov.get("engine_version") or a["version"]
    prov["harness_sha256"] = _sha256_file(os.path.abspath(__file__))

    core = {
        "strategy": strategy,
        "params": params,
        "inputs": [[i["path"], i["sha256"], i["bars"]] for i in inputs],
        "engine_sha256": prov["engine_sha256"],
        "engine_version": prov["engine_version"],
    }
    run_id = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
    cmd = f"python code/vrun.py run --strategy {strategy} --tf {tf} --symbol {symbol}"
    if params:
        cmd += f" --params '{json.dumps(params, sort_keys=True)}'"
    return {
        "schema": SCHEMA, "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "strategy": strategy, "symbol": symbol, "timeframe": tf,
        "params": params, "provenance": prov, "inputs": inputs,
        "metrics": metrics, "tables": tables, "core": core, "cmd": cmd,
    }


def artifact_path(run_id: str) -> str:
    return os.path.join(RUNS, run_id + ".json")


def save_artifact(a: dict) -> str:
    os.makedirs(RUNS, exist_ok=True)
    p = artifact_path(a["run_id"])
    with open(p, "w", encoding="utf-8") as f:
        json.dump(a, f, indent=2, sort_keys=True)
    return p


def load_artifact(run_id: str) -> dict:
    p = artifact_path(run_id)
    if not os.path.exists(p):
        raise FileNotFoundError(
            f"REFUSED: no artifact {p}. A number without an artifact is not a result.")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _fmt(a: dict) -> str:
    m = a["metrics"]
    out = [
        f"run_id   : {a['run_id']}",
        f"strategy : {a['strategy']}  {a['symbol']} {a['timeframe']}",
        f"engine   : {a['provenance'].get('engine_version')}  "
        f"sha {str(a['provenance'].get('engine_sha256'))[:12]}",
        f"data     : {len(a['inputs'])} file(s)",
    ]
    for i in a["inputs"]:
        out.append(f"           {os.path.basename(i['path'])}  {i['bars']} bars  "
                   f"{i['start'][:10]}..{i['end'][:10]}  sha {i['sha256'][:12]}")
    out += [f"params   : {json.dumps(a['params'], sort_keys=True)}", "---"]
    for k in ("n_trades", "return_pct", "profit_factor", "win_rate", "expectancy_R",
              "max_dd_pct", "fees", "final_equity", "flag", "window", "n_strategies",
              "n_pass", "best_net_t", "best_net_t_id", "hold_minutes", "horizon_bars",
              "train_bars", "bh_return_pct", "cost_bp_roundtrip", "t_crit_bonferroni"):
        if k in m:
            out.append(f"{k:<16}: {m[k]}")
    if a.get("tables"):
        out.append(f"tables   : {len(a['tables'])} rows (see JSON; not shown)")
    return "\n".join(out)


# ══════════════════════════════════════════════ commands
def parse_params(ns) -> dict:
    d = {}
    if getattr(ns, "params", ""):
        d.update(json.loads(ns.params))
    for kv in (getattr(ns, "set", None) or []):
        k, _, v = kv.partition("=")
        if not v:
            raise ValueError(f"--set expects key=value, got {kv!r}")
        if v.lower() in ("true", "false"):
            val = v.lower() == "true"
        else:
            try:
                val = int(v)
            except ValueError:
                try:
                    val = float(v)
                except ValueError:
                    val = v
        d[k] = val
    return d


def cmd_run(args):
    a = make_artifact(args.strategy, args.tf, args.symbol, parse_params(args))
    print(_fmt(a))
    print("artifact      :", save_artifact(a))
    return 0


def cmd_render(args):
    print(_fmt(load_artifact(args.run_id)))
    return 0


def _same(x, y) -> bool:
    return json.dumps(x, sort_keys=True, default=str) == json.dumps(y, sort_keys=True, default=str)


def cmd_verify(args):
    a = load_artifact(args.run_id)
    # Binding check BEFORE anything else: the stored core must hash to the id
    # it claims. Without this, an artifact whose params AND metrics were edited
    # together would re-run cleanly under a stale id (the qbt-audit Probe-B
    # class). Derivation is unchanged, so no artifact written by make_artifact
    # can fail here.
    core_id = hashlib.sha256(json.dumps(a.get("core", {}), sort_keys=True,
                                        separators=(",", ":")).encode()).hexdigest()[:16]
    if a.get("run_id") != core_id or core_id != args.run_id:
        print("REFUSED: artifact content does not hash to its run_id "
              f"({core_id} vs {a.get('run_id')}/{args.run_id}). Tampering or a "
              "cross-written id — do not publish numbers from it.")
        return 2
    strat = a.get("strategy")
    if strat in ADAPTERS:
        sources = ADAPTERS[strat].get("sources", [])
        for src in sources:
            if not os.path.exists(src):
                print(f"ORPHANED: engine source is missing from disk ({os.path.basename(src)}). "
                      f"Artifact {args.run_id} is permanently orphaned (known killed).")
                return 4
    try:
        b = make_artifact(a["strategy"], a["timeframe"], a["symbol"], a["params"])
    except FileNotFoundError as e:
        print(f"REFUSED: input file missing: {e}")
        return 2
    ca, cb = a["core"], b["core"]
    for k in ("engine_sha256", "engine_version", "params", "strategy"):
        if ca.get(k) != cb.get(k):
            print(f"REFUSED: {k} drifted since the artifact was written "
                  f"({str(ca.get(k))[:24]} -> {str(cb.get(k))[:24]}). Treat as tampering.")
            return 2
    if ca["inputs"] != cb["inputs"]:
        for x, y in zip(ca["inputs"], cb["inputs"]):
            if x != y:
                print(f"STALE: data changed since the artifact: {os.path.basename(x[0])} "
                      f"{x[2]} -> {y[2]} bars (sha {x[1][:12]} -> {y[1][:12]}).")
        print("The artifact is a frozen snapshot of the OLD bytes; re-run to refresh. "
              "Not a fabrication.")
        return 3
    if not _same(a["metrics"], b["metrics"]) or not _same(a.get("tables"), b.get("tables")):
        print("REFUSED: metrics do not reproduce (engine non-determinism).")
        for k in sorted(set(a["metrics"]) | set(b["metrics"])):
            av, bv = a["metrics"].get(k), b["metrics"].get(k)
            if not _same(av, bv):
                print(f"    {k}: artifact={av} recomputed={bv}")
        return 2
    h_old = (a.get("provenance") or {}).get("harness_sha256")
    h_new = (b.get("provenance") or {}).get("harness_sha256")
    note = "" if h_old == h_new else f"  (harness rebuilt: {str(h_old)[:12]} -> {str(h_new)[:12]})"
    print(f"OK: {a['run_id']} reproduces bit-for-bit.{note}")
    return 0


def _iter_combos(tfs, dirs=None):
    dirs = dirs or TF_DIR
    for tf in tfs:
        if tf not in dirs:
            continue
        d, suf = dirs[tf]
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(f"_{suf}.csv"):
                yield tf, fn.replace(f"_{suf}.csv", "")


def _first(d, *keys):
    """First key present in `d` (None-safe) — adapters report different metric names."""
    for k in keys:
        if k in d:
            return d[k]
    return None


def _f(v, width=0, prec=None):
    """Format a possibly-None number for console output."""
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return f"{'—':>{width}}" if width else "—"
    txt = f"{v:>{width}.{prec}f}" if prec is not None else f"{v:>{width}}" if width else f"{v}"
    return txt


def _matrix_cols(art):
    """Metric columns for the matrix index, tolerating each adapter's own dialect."""
    m = art["metrics"]
    n = _first(m, "n_trades")
    ret = _first(m, "return_pct", "best_net_pct")
    pf = _first(m, "profit_factor", "best_pf")
    dd = _first(m, "max_dd_pct")
    flag = _first(m, "flag")
    if flag is None and m.get("n_strategies"):
        flag = f"{m.get('n_pf_gt_1p2_n30', 0)}/{m['n_strategies']} pass"
    if n is None or dd is None:
        # Per-symbol adapters that report a TABLE of strategies (cbpack) have no
        # single trade count. Take it from the row the headline return came from.
        # Do NOT fall back to m["n_ok"]: that is a count of STRATEGIES, and
        # labelling it `n_trades` would make a 200-trade cell read as 9 trades.
        bid = m.get("best_net_id")
        row = next((r for r in (art.get("tables") or []) if r.get("id") == bid), None) or {}
        if n is None:
            n = row.get("trades")
        if dd is None:
            dd = row.get("maxDD_%")
    return n, ret, pf, dd, flag


def _write_matrix_index(strategy, rows):
    os.makedirs(RUNS, exist_ok=True)
    idx = os.path.join(RUNS, f"_matrix_{strategy}.csv")
    pd.DataFrame(rows, columns=["tf", "symbol", "run_id", "n_trades", "return_pct",
                                "profit_factor", "max_dd_pct", "flag"]).to_csv(idx, index=False)
    print("\nindex:", idx)
    return idx


def cmd_matrix(args):
    a = ADAPTERS[args.strategy]
    if not a["matrix"]:
        print(f"REFUSED: strategy '{args.strategy}' is not per-symbol; use `run`.")
        return 2
    params = parse_params(args)
    tfs = args.tf.split(",") if args.tf else ["1h", "15m", "5m", "1m"]

    # --index-only rebuilds the index FROM THE ARTIFACTS instead of re-running
    # them. Use it when an index is missing or was written by an older harness:
    # re-running would rewrite good artifacts, and re-writing evidence to fix a
    # cosmetic index is exactly the wrong trade.
    if getattr(args, "index_only", False):
        rows = []
        for p in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
            if os.path.basename(p).startswith("_"):
                continue
            with open(p, encoding="utf-8") as f:
                art = json.load(f)
            if art.get("schema") != SCHEMA or art.get("strategy") != args.strategy:
                continue
            gp = art.get("params") or {}
            if set(gp) & {"slice_from", "slice_to", "mode", "ids"} or gp != params:
                continue
            n, ret, pf, dd, flag = _matrix_cols(art)
            rows.append((art["timeframe"], art["symbol"], art["run_id"], n, ret, pf, dd, flag))
        _write_matrix_index(args.strategy, rows)
        print(f"{len(rows)} artifacts indexed")
        return 0

    rows = []
    for tf, sym in _iter_combos(tfs, a.get("matrix_dirs")):
        try:
            art = make_artifact(args.strategy, tf, sym, params)
            save_artifact(art)
            n, ret, pf, dd, flag = _matrix_cols(art)
            rows.append((tf, sym, art["run_id"], n, ret, pf, dd, flag))
            print(f"{tf:>4} {sym:<10} {art['run_id']}  n={str(n):>6} "
                  f"ret%={_f(ret, 9, 2)} PF={_f(pf)} "
                  f"DD%={_f(dd, 8, 2)} {flag}", flush=True)
        except Exception as e:
            print(f"{tf:>4} {sym:<10} ERROR {type(e).__name__} {e}", flush=True)
    _write_matrix_index(args.strategy, rows)
    return 0


# ── parallel matrix / verify ─────────────────────────────────────────────
# ADDITIVE commands. `pmatrix` and `pverify` run the SAME code paths as
# `matrix` and `verify` (make_artifact + save_artifact; cmd_verify VERBATIM,
# captured, not reimplemented) across a process pool. No existing command,
# adapter or artifact layout changes, and harness_sha256 is not part of an
# artifact's core, so adding commands cannot invalidate any run_id. Workers
# are spawned processes: make_artifact is deterministic (every engine's audit
# proves it), so a parallel run writes byte-identical artifacts and run_ids.

def _default_workers():
    return max(1, min(8, os.cpu_count() or 4))


def _pmatrix_one(job):
    """One (tf, symbol) cell in a worker process."""
    strategy, tf, sym, params = job
    try:
        art = make_artifact(strategy, tf, sym, params)
        save_artifact(art)
        n, ret, pf, dd, flag = _matrix_cols(art)
        line = (f"{tf:>4} {sym:<10} {art['run_id']}  n={str(n):>6} "
                f"ret%={_f(ret, 9, 2)} PF={_f(pf)} "
                f"DD%={_f(dd, 8, 2)} {flag}")
        row = (tf, sym, art["run_id"], n, ret, pf, dd, flag)
        return ("ok", tf, sym, line, row)
    except Exception as e:
        return ("err", tf, sym, f"{tf:>4} {sym:<10} ERROR {type(e).__name__} {e}", None)


def cmd_pmatrix(args):
    a = ADAPTERS[args.strategy]
    if not a["matrix"]:
        print(f"REFUSED: strategy '{args.strategy}' is not per-symbol; use `run`.")
        return 2
    params = parse_params(args)
    tfs = args.tf.split(",") if args.tf else ["1h", "15m", "5m", "1m"]
    combos = list(_iter_combos(tfs, a.get("matrix_dirs")))
    if not combos:
        print("no combos found for tf(s): " + (args.tf or "(default)"))
        return 2
    from concurrent.futures import ProcessPoolExecutor, as_completed
    n_workers = max(1, min(args.workers, len(combos)))
    print(f"pmatrix {args.strategy} params={json.dumps(params, sort_keys=True)} "
          f"cells={len(combos)} workers={n_workers}", flush=True)
    results = {}
    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        futs = [ex.submit(_pmatrix_one, (args.strategy, tf, sym, params))
                for tf, sym in combos]
        for fut in as_completed(futs):
            _st, tf, sym, line, row = fut.result()
            print(line, flush=True)
            if row is not None:
                results[(tf, sym)] = row
    # index in the SAME deterministic order `matrix` writes (tf order, then
    # sorted symbol filenames), so parallel and sequential runs of the same
    # grid produce an identical index file
    rows = [results[c] for c in combos if c in results]
    _write_matrix_index(args.strategy, rows)
    return 0


def _pverify_one(run_id):
    """One artifact verification in a worker process, through the EXISTING
    cmd_verify (output captured, exit code kept) — parallel verify is the
    sequential verify, not a second implementation of it."""
    buf = io.StringIO()
    ns = argparse.Namespace(run_id=run_id)
    try:
        with contextlib.redirect_stdout(buf):
            rc = cmd_verify(ns)
    except Exception as e:
        return run_id, 2, f"REFUSED: worker exception {type(e).__name__}: {e}"
    return run_id, rc, buf.getvalue().strip()


def cmd_pverify(args):
    if args.ids:
        run_ids = [x.strip() for x in args.ids.split(",") if x.strip()]
    elif args.strategy:
        run_ids = []
        for p in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
            if os.path.basename(p).startswith("_"):
                continue
            with open(p, encoding="utf-8") as f:
                art = json.load(f)
            if art.get("strategy") == args.strategy:
                run_ids.append(art["run_id"])
    else:
        print("pverify: give --strategy <name> or --ids <id1,id2,...>")
        return 2
    if not run_ids:
        print(f"pverify: no artifacts found for strategy {args.strategy!r}")
        return 2
    from concurrent.futures import ProcessPoolExecutor, as_completed
    n_workers = max(1, min(args.workers, len(run_ids)))
    print(f"pverify {len(run_ids)} artifact(s), workers={n_workers}", flush=True)
    n_ok = n_stale = n_refused = n_orphaned = 0
    failures = []
    skip_orphaned = getattr(args, "skip_orphaned", False)
    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        futs = [ex.submit(_pverify_one, rid) for rid in run_ids]
        for fut in as_completed(futs):
            rid, rc, out = fut.result()
            if rc == 0:
                n_ok += 1
                if not args.quiet:
                    first = out.splitlines()[0] if out else ""
                    print(f"OK       {rid}  {first}", flush=True)
            elif rc == 4:
                n_orphaned += 1
                if not skip_orphaned:
                    failures.append((rid, rc, out))
                    print(f"ORPHANED {rid}", flush=True)
                elif not args.quiet:
                    print(f"ORPHANED {rid}  (skipped)", flush=True)
            elif rc == 3:
                n_stale += 1
                failures.append((rid, rc, out))
                print(f"STALE    {rid}", flush=True)
            else:
                n_refused += 1
                failures.append((rid, rc, out))
                print(f"RC={rc}   {rid}", flush=True)
    print("---")
    for rid, rc, out in sorted(failures):
        print(f"[{rid}] rc={rc}\n{out}")
    print(f"pverify: {n_ok} OK, {n_stale} STALE, {n_orphaned} ORPHANED, {n_refused} REFUSED "
          f"(of {len(run_ids)}); exit code reports the worst case")
    if n_refused:
        return 2
    if n_stale:
        return 3
    if n_orphaned and not skip_orphaned:
        return 4
    return 0


# ── guard ────────────────────────────────────────────────────────────────
# PROVENANCE check, not a correctness check: it answers "is this number backed
# by a cited artifact?", never "is this number right?". It passed on a report
# whose builder was double-counting cells, so assert totals yourself.
RUNID_RE = re.compile(r"\b[0-9a-fA-F]{16}\b")
HEXWORD_RE = re.compile(r"\b[0-9a-fA-F]{8,}\b")
# A sign only counts as a sign when it is NOT glued to a preceding digit/word.
# Without the lookbehind, the range "0.652-1.788" tokenises as 0.652 and -1.788,
# and guard then reports an unbacked NEGATIVE number that is not in the report at
# all -- a false refusal on any table that prints a min-max range.
NUMBER_RE = re.compile(r"(?<![\w.])[+-]?\d+(?:\.\d+)?")


def _collect_numbers(obj, out: list) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, dict):
        for v in obj.values():
            _collect_numbers(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _collect_numbers(v, out)
    elif isinstance(obj, (int, float, np.integer, np.floating)):
        v = float(obj)
        if np.isfinite(v):
            out.append(v)
    elif isinstance(obj, str):
        # numbers embedded in stored strings (dates, ids) are quotable too
        for t in NUMBER_RE.findall(obj):
            try:
                out.append(float(t))
            except ValueError:
                pass


def cmd_guard(args):
    text = open(args.report, encoding="utf-8").read()
    lines = text.splitlines()
    cited, backers = [], []
    cited_line_map = {}
    for line_idx, line in enumerate(lines):
        for m in RUNID_RE.findall(line):
            if m not in cited_line_map:
                cited_line_map[m] = []
            cited_line_map[m].append((line_idx + 1, line))
            if m in cited:
                continue
            if os.path.exists(artifact_path(m)):
                cited.append(m)
                backers.append(load_artifact(m))

    if getattr(args, "strict", False):
        if not cited:
            print("GUARD --strict: REFUSED — no valid run_id cited in report.")
            return 2
        for rid, art in zip(cited, backers):
            art_sym = art.get("symbol", "").upper()
            art_tf = art.get("timeframe", "").lower()
            for line_no, line_text in cited_line_map.get(rid, []):
                upper_line = line_text.upper()
                all_syms = re.findall(r"\b[A-Z0-9]{3,10}USDT\b", upper_line)
                for s in all_syms:
                    if s != art_sym and s in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT",
                                              "SUIUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT",
                                              "HYPEUSDT", "SPXUSDT", "JUPUSDT"):
                        print(f"GUARD --strict: REFUSED — symbol context mismatch on line {line_no}: "
                              f"line cites '{s}' but run_id {rid} is for '{art_sym}'.")
                        return 2

    values = []
    for a in backers:
        _collect_numbers(a.get("metrics"), values)
        _collect_numbers(a.get("tables"), values)
        _collect_numbers(a.get("inputs"), values)
        # `params` records what the run WAS ASKED for -- a slice report necessarily
        # quotes its slice dates, and those live here ("2025-06-14"). Not scanned:
        # `cmd` and `created_utc`, which are provenance metadata, not measurements;
        # scanning `cmd` would let a report quote any number by embedding it in a
        # command line.
        _collect_numbers(a.get("params"), values)

    scan = HEXWORD_RE.sub(" ", text)          # run_ids / hashes are ids, not metrics
    unbacked, seen = [], set()
    for tok in NUMBER_RE.findall(scan):
        try:
            val = float(tok)
        except ValueError:
            continue
        dps = len(tok.split(".")[1]) if "." in tok else 0
        if any(abs(round(v, dps) - val) < 1e-9 for v in values):
            continue
        if tok in seen:
            continue
        seen.add(tok)
        unbacked.append(tok)

    if unbacked:
        print("GUARD: REFUSED — report contains numbers with no artifact behind them:")
        for t in unbacked:
            print(f"  - unbacked number: {t}")
        return 2
    print(f"GUARD: OK {'(strict)' if getattr(args, 'strict', False) else ''} — every metric number is backed by {cited}")
    return 0


def cmd_stale(args):
    """Audit artifacts against current data files on disk."""
    filter_data = args.data.lower() if getattr(args, "data", None) else None
    all_arts = sorted(glob.glob(os.path.join(RUNS, "*.json")))
    n_checked = 0
    stale_count = 0
    ok_count = 0
    missing_count = 0

    file_cache = {}
    def check_file(p):
        if p not in file_cache:
            if not os.path.exists(p):
                file_cache[p] = None
            else:
                file_cache[p] = (_sha256_file(p), _read_input(p)["bars"])
        return file_cache[p]

    stale_entries = []
    for p in all_arts:
        if os.path.basename(p).startswith("_"):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                art = json.load(f)
        except Exception:
            continue
        rid = art.get("run_id", os.path.basename(p)[:-5])
        inputs = art.get("inputs", [])
        matched_inputs = []
        for inp in inputs:
            ipath = inp.get("path", "")
            if filter_data is None or filter_data in ipath.lower():
                matched_inputs.append(inp)

        if not matched_inputs:
            continue

        n_checked += 1
        is_stale = False
        is_missing = False
        reasons = []

        for inp in matched_inputs:
            ipath = inp["path"]
            current = check_file(ipath)
            if current is None:
                is_missing = True
                reasons.append(f"file missing: {os.path.basename(ipath)}")
                break
            cur_sha, cur_bars = current
            if cur_sha != inp.get("sha256") or cur_bars != inp.get("bars"):
                is_stale = True
                reasons.append(f"{os.path.basename(ipath)}: artifact {inp.get('bars')} bars ({inp.get('sha256','')[:8]}) "
                               f"-> disk {cur_bars} bars ({cur_sha[:8]})")

        meta = f"{art.get('strategy','?'):<10} {art.get('symbol','?'):<10} {art.get('timeframe','?'):<4}"
        if is_missing:
            missing_count += 1
            stale_entries.append((rid, "DATA_MISSING", meta, ", ".join(reasons)))
        elif is_stale:
            stale_count += 1
            stale_entries.append((rid, "STALE", meta, ", ".join(reasons)))
        else:
            ok_count += 1
            if not getattr(args, "quiet", False) and filter_data:
                print(f"OK       {rid} {meta}")

    if stale_entries:
        print(f"\n--- Stale / Missing Artifacts ({len(stale_entries)}) ---")
        for rid, status, meta, detail in stale_entries:
            print(f"{status:<12} {rid} {meta} | {detail}")

    print("---")
    print(f"stale summary: {ok_count} OK, {stale_count} STALE, {missing_count} DATA_MISSING "
          f"(checked {n_checked} matching artifacts)")
    return 3 if stale_count else (2 if missing_count else 0)


def cmd_stats(args):
    """Institutional quant scorecard for an artifact."""
    sys.path.insert(0, CODE)
    import quant_metrics as qm

    art = load_artifact(args.run_id)
    card = qm.compute_artifact_scorecard(art)
    print(f"=== QUANT STATS SCORECARD: {card['run_id']} ===")
    print(f"Strategy : {card['strategy']} | Symbol: {card['symbol']} | Timeframe: {card['timeframe']}")
    print(f"Trades   : {card['n_trades']} | Win Rate: {art['metrics'].get('win_rate')}")
    print(f"Return % : {card['return_pct']}% | Profit Factor: {card['profit_factor']} | MaxDD: {card['max_dd_pct']}%")
    print("\n[1] Risk-Adjusted Return Metrics")
    print(f"  Annualized Sharpe Ratio : {card['sharpe_annualized']}")
    print(f"  Annualized Sortino Ratio: {card['sortino_annualized']}")
    print(f"  Calmar Ratio            : {card['calmar_ratio']}")
    print("\n[2] Serial Correlation & Independence (Ljung-Box Test)")
    lb = card["autocorrelation_ljung_box"]
    if lb:
        print(f"  Q-Stat: {lb.get('q_stat')} | p-val: {lb.get('p_val')} | Lags: {lb.get('lags')}")
        print(f"  Hypothesis: {'REJECTED (autocorrelated returns)' if lb.get('reject_iid') else 'ACCEPTED (i.i.d. consistent)'}")
    else:
        print("  (No per-trade PnL series available in artifact)")
    print("\n[3] Stationary Block Bootstrap (95% CI)")
    bb = card["block_bootstrap"]
    if bb:
        print(f"  Mean: {bb.get('mean')} | 95% CI: [{bb.get('ci_lo')}, {bb.get('ci_hi')}] | t-stat: {bb.get('t_stat')}")
        print(f"  P(mean <= 0): {bb.get('p_le_zero')} | Block Size: {bb.get('block_size')} | Draws: {bb.get('draws')}")
    else:
        print("  (No trade samples for bootstrap)")
    print("\n[4] Liquidation & Margin Buffer Verification")
    lq = card["liquidation_check"]
    if lq:
        print(f"  Min Margin Buffer : {lq.get('min_margin_buffer_pct')}%")
        print(f"  Max Gross Leverage: {lq.get('max_leverage_reached')}x")
        print(f"  Bars Over Leverage: {lq.get('bars_over_leverage')}")
        print(f"  Liquidation Breach: {'YES (CRITICAL)' if lq.get('liquidation_occurred') else 'NO (Safe)'}")
    else:
        print("  (Margin buffer metrics not recorded for this adapter)")
    print("\n[5] Tail Risk (Historical VaR / CVaR, loss magnitudes in %)")
    vc = card.get("var_cvar")
    if vc:
        if vc.get("n_days"):
            print(f"  Daily  ({vc['n_days']} days x {vc['bars_per_day']} bars): "
                  f"VaR95 {vc.get('var_95_pct')}% | CVaR95 {vc.get('cvar_95_pct')}% | "
                  f"VaR99 {vc.get('var_99_pct')}% | CVaR99 {vc.get('cvar_99_pct')}%")
        if vc.get("bar_n_obs"):
            print(f"  Per-bar ({vc['bar_n_obs']} obs): "
                  f"VaR95 {vc.get('bar_var_95_pct')}% | CVaR95 {vc.get('bar_cvar_95_pct')}% | "
                  f"VaR99 {vc.get('bar_var_99_pct')}% | CVaR99 {vc.get('bar_cvar_99_pct')}%")
    else:
        print("  (No equity curve in artifact — VaR/CVaR not computable)")
    return 0


def cmd_neighborhood(args):
    """Evaluates parameter neighborhood stability."""
    vals = [v.strip() for v in args.values.split(",") if v.strip()]
    if not vals:
        print("neighborhood: give --values v1,v2,v3")
        return 2
    param_name = args.param
    print(f"Neighborhood stability sweep: {args.strategy} {args.symbol} {args.tf} on '{param_name}' across {vals}")
    results = []
    for v in vals:
        try:
            val = float(v) if "." in v else int(v)
        except ValueError:
            val = v
        p = {param_name: val}
        try:
            art = make_artifact(args.strategy, args.tf, args.symbol, p)
            save_artifact(art)
            m = art["metrics"]
            pf = _first(m, "profit_factor", "best_pf")
            ret = _first(m, "return_pct", "best_net_pct")
            n = _first(m, "n_trades")
            dd = _first(m, "max_dd_pct")
            results.append((v, art["run_id"], pf, ret, n, dd, "OK" if pf and pf > 1.2 else "FAIL"))
            print(f"  {param_name}={v:<8} run_id={art['run_id']} PF={_f(pf, 5, 2)} Ret%={_f(ret, 7, 2)} "
                  f"n={str(n):>5} DD%={_f(dd, 6, 2)}")
        except Exception as e:
            print(f"  {param_name}={v:<8} ERROR: {e}")
            results.append((v, None, None, None, None, None, "ERROR"))

    valid_pfs = [r[2] for r in results if r[2] is not None and isinstance(r[2], (int, float))]
    if valid_pfs:
        min_pf, max_pf, std_pf = min(valid_pfs), max(valid_pfs), float(np.std(valid_pfs))
        is_stable = bool(min_pf >= 1.0 and (max_pf - min_pf) < 0.5)
        print("---")
        print(f"Neighborhood Verdict: min PF={min_pf:.2f}, max PF={max_pf:.2f}, std={std_pf:.3f} "
              f"-> {'STABLE' if is_stable else 'CLIFF / SENSITIVE'}")
    return 0


def cmd_show(args):
    if not os.path.isdir(RUNS):
        print("no artifacts yet")
        return 0
    n = 0
    for fn in sorted(os.listdir(RUNS)):
        if fn.endswith(".json") and not fn.startswith("_"):
            a = load_artifact(fn[:-5])
            print(f"{a['run_id']}  {a['strategy']:<9} {a['symbol']:<10} {a['timeframe']:<4} "
                  f"PF={a['metrics'].get('profit_factor')}  ret%={a['metrics'].get('return_pct')}")
            n += 1
    print(f"-- {n} artifacts --")
    return 0


def main():
    ap = argparse.ArgumentParser(prog="vrun")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run")
    r.add_argument("--strategy", required=True, choices=list(ADAPTERS))
    r.add_argument("--tf", required=True)
    r.add_argument("--symbol", required=True)
    r.add_argument("--params", default="")
    r.add_argument("--set", action="append")
    r.set_defaults(fn=cmd_run)

    rd = sub.add_parser("render")
    rd.add_argument("run_id")
    rd.set_defaults(fn=cmd_render)

    v = sub.add_parser("verify")
    v.add_argument("run_id")
    v.set_defaults(fn=cmd_verify)

    mx = sub.add_parser("matrix")
    mx.add_argument("--strategy", required=True, choices=list(ADAPTERS))
    mx.add_argument("--tf", default="")
    mx.add_argument("--index-only", action="store_true", dest="index_only",
                    help="rebuild the index CSV from existing artifacts; do not re-run")
    mx.add_argument("--params", default="")
    mx.add_argument("--set", action="append")
    mx.set_defaults(fn=cmd_matrix)

    pm = sub.add_parser("pmatrix",
                        help="parallel matrix: same cells, index and artifacts as matrix")
    pm.add_argument("--strategy", required=True, choices=list(ADAPTERS))
    pm.add_argument("--tf", default="")
    pm.add_argument("--params", default="")
    pm.add_argument("--set", action="append")
    pm.add_argument("--workers", type=int, default=_default_workers())
    pm.set_defaults(fn=cmd_pmatrix)

    pv = sub.add_parser("pverify",
                        help="parallel verify of many artifacts (read-only)")
    pv.add_argument("--strategy", default="",
                    help="verify every artifact of this strategy")
    pv.add_argument("--ids", default="",
                    help="comma-separated run_ids to verify")
    pv.add_argument("--workers", type=int, default=_default_workers())
    pv.add_argument("--quiet", action="store_true",
                    help="print only failures and the summary")
    pv.add_argument("--skip-orphaned", action="store_true",
                    help="ignore orphaned artifacts (missing engine files) in exit code")
    pv.set_defaults(fn=cmd_pverify)

    g = sub.add_parser("guard")
    g.add_argument("--report", required=True)
    g.add_argument("--strict", action="store_true",
                   help="enforce context verification (symbol/timeframe alignment in cited lines)")
    g.set_defaults(fn=cmd_guard)

    st = sub.add_parser("stale",
                        help="audit artifacts against current data files on disk")
    st.add_argument("--data", default="",
                    help="filter to artifacts using this data file (substring match)")
    st.add_argument("--quiet", action="store_true",
                    help="print only stale or missing artifacts")
    st.set_defaults(fn=cmd_stale)

    stt = sub.add_parser("stats",
                         help="institutional quant scorecard (Sharpe, Sortino, Calmar, Ljung-Box, bootstrap, liquidation)")
    stt.add_argument("run_id")
    stt.set_defaults(fn=cmd_stats)

    nh = sub.add_parser("neighborhood",
                        help="sweep parameter neighborhood and assess stability")
    nh.add_argument("--strategy", required=True, choices=list(ADAPTERS))
    nh.add_argument("--tf", required=True)
    nh.add_argument("--symbol", required=True)
    nh.add_argument("--param", required=True)
    nh.add_argument("--values", required=True,
                    help="comma-separated parameter values, e.g. 0.08,0.10,0.12")
    nh.set_defaults(fn=cmd_neighborhood)

    sh = sub.add_parser("show")
    sh.set_defaults(fn=cmd_show)

    a = ap.parse_args()
    try:
        rc = a.fn(a)
    except FileNotFoundError as e:
        print(str(e))
        rc = 2
    except ValueError as e:
        print(f"REFUSED: {e}")
        rc = 2
    sys.exit(rc if isinstance(rc, int) else 0)


if __name__ == "__main__":
    main()
