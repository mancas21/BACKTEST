#!/usr/bin/env python
"""pack20_wrap.py -- harness runner for the twenty-strategy pack (2026-11-08).

Source of record: Downloads/strategy_pack_20.py, copied BYTE-IDENTICAL to
code/pack20_engine.py (sha256 48aecbdddd21f8747296d75515523404c8712addc1cf573d418f45061a693298).
One artifact = one strategy id (--set id=1..20, file order 01..20) on ONE
declared market. Every number comes from the pack's OWN machinery: its signal
functions (STRATEGIES[key](df, p)) and its own event-loop executor
(run_backtest). Execution conventions as the pack declares: entries fill at
the NEXT bar's open, signal exits fill at the signal bar's CLOSE, brackets
fill intrabar AT THE LEVEL, a bar with both SL and TP fills the STOP first,
max_hold exits at the close, sizing is full-equity compounding at 1x, one
position at a time, end-of-data closes at the last close.

Measured INSIDE every artifact (never derived by the reader):
  * repo gate cost     5.0 fee + 0.5 slip bps per side (11 bps RT)  <- verdict
  * zero-cost control  the gross edge (separates "no edge" from "cost ate it")
  * pack cost control  5.0 fee + 2.0 slip bps (the pack's shipped default;
                       sensitivity only, never the gate)
  * 70/30 OOS split on entry time (oos_profit_factor, oos_return_pct)
  * equal thirds (n_periods_green), best-5 concentration
    (best5_share_pct over NET PnL; conc_net_without_top5_pct = simple PnL
    subtraction on the initial-equity base, non-compounded, declared)
  * per-trade bootstrap CI (deterministic seed, iid resample)
  * buy & hold over the same window, yearly PnL map.

DECLARED LIMITS (audit findings, full list in results/pack20_report.md):
  * funding NOT charged -- the engine has no funding ledger. Measured funding
    drag on prior directional-pack survivors was -3.45 to -6.11pp over full
    windows (cbpackf artifacts). Any survivor must be re-run with funding
    before any live claim.
  * bracket fills use the LEVEL even when the open gaps through it (the
    pack's convention; optimistic on gap bars -- the template executor's
    min(px, stop) fix is NOT applied, the pack runs verbatim).
  * equity is realized-cash only (no mark-to-market while a position is
    open): max drawdown is UNDERSTATED.
  * audit findings A1/A2 are inflationary and run VERBATIM here:
    A1  _levels_htf exposes a 4h pivot one 4h-bar early (the pivot window
        includes bar i+rb but the level is appended at T[i+rb], that bar's
        OPEN) -> affects 01_liq_fvg only.
    A2  _walkforward trains on rows [t0-train, t0) with a 4-bar label
        horizon (y[t0-1] uses close[t0+3]): unpurged label split ->
        affects 18_logreg and 20_gbm.
    A passing cell of 01/18/20 requires a patched re-run before any
    CANDIDATE claim (the patched variant is NOT built unless needed).

Loader conventions: kline CSVs (open_ts ms epoch) -> UTC DatetimeIndex, so
asian_sweep hours, vwap_fade days and _levels_htf resamples are all UTC
(Binance klines are UTC-native). Duplicates dropped, sorted ascending.
"""
from __future__ import annotations

import importlib.util
import os

import numpy as np
import pandas as pd

ENGINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "pack20_engine.py")
ENGINE_SHA256 = "48aecbdddd21f8747296d75515523404c8712addc1cf573d418f45061a693298"

spec = importlib.util.spec_from_file_location("pack20_engine", ENGINE_PATH)
P20 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P20)
STRATEGIES = P20.STRATEGIES
KEYS = list(STRATEGIES.keys())          # "01_liq_fvg" .. "20_gbm_walkforward"

REPO = dict(fees_bps=5.0, slippage_bps=0.5)     # verdict cost (11 bps RT)
ZERO = dict(fees_bps=0.0, slippage_bps=0.0)     # gross edge control
PACK_DEFAULT = dict(fees_bps=5.0, slippage_bps=2.0)  # pack shipped default

RESERVED = {"id", "boot_seed", "boot_draws"}
BOOT_SEED_DEFAULT = 20261108
BOOT_DRAWS_DEFAULT = 10000

FILL_MODEL = "taker_next_open_brackets_intrabar"


def load_df(path: str) -> pd.DataFrame:
    """Kline CSV -> UTC-indexed OHLCV frame the pack functions expect."""
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    df["open_ts"] = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
    df = df.drop_duplicates("open_ts").sort_values("open_ts").reset_index(drop=True)
    df = df.set_index("open_ts")
    for c in ("open", "high", "low", "close", "volume"):
        if c not in df.columns:
            raise ValueError(f"{path}: missing column {c!r}")
        df[c] = df[c].astype(float)
    return df[["open", "high", "low", "close", "volume"]]


def _pf(pnls: np.ndarray):
    """(profit_factor_or_None, no_losses). None with no losers: JSON cannot
    carry inf, and the flag states it instead of a fudged number."""
    if len(pnls) == 0:
        return None, False
    gp = float(pnls[pnls > 0].sum())
    gl = float(-pnls[pnls < 0].sum())
    if gl <= 0.0:
        return None, bool(gp > 0.0)
    return gp / gl, False


def _boot_ci(rets: np.ndarray, seed: int, draws: int):
    """Percentile bootstrap of the MEAN per-trade return, iid resample.
    Units: bps of entry cash per trade (1e-4). Deterministic seed."""
    n = len(rets)
    if n < 2:
        return None, None
    rng = np.random.default_rng(seed)
    means = np.empty(draws)
    for b in range(draws):
        means[b] = rets[rng.integers(0, n, n)].mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo * 1e4), float(hi * 1e4)


def _cost_row(rid: str, tr: pd.DataFrame, eqs: pd.Series) -> dict:
    pnls = tr["pnl"].to_numpy(float) if len(tr) else np.zeros(0)
    pf, noloss = _pf(pnls)
    return {"id": rid, "kind": "cost",
            "net_pct": float(eqs.iloc[-1] - 1.0) * 100.0,
            "pf": pf, "pf_no_losses": noloss,
            "n": int(len(tr)),
            "win_rate_pct": (float(tr["win"].mean()) * 100.0
                             if len(tr) else None)}


def _metrics(df, sig, repo, zero, pack, key, sid, params) -> tuple[dict, list]:
    tr_r, eq_r, m_r = repo
    eq = eq_r                       # realized-cash curve, index = bar time
    n_bars = len(df)

    m = {
        "strategy_id": sid, "strategy_name": key,
        "bars": int(n_bars),
        "window_start": str(df.index[0]), "window_end": str(df.index[-1]),
        "fill_model": FILL_MODEL,
        "funding_charged": False,
        "funding_model": "none (declared; engine has no funding ledger)",
        "fee_bps_per_side": 5.0, "slippage_bps_per_side": 0.5,
        "cost_bp_roundtrip": 11.0,
        "pack_default_cost_bp_roundtrip": 14.0,
        "sizing": "full-equity compounding, 1x, one position at a time",
        "gap_fill": "bracket fills AT THE LEVEL even when the open gaps "
                    "through (pack convention, optimistic on gap bars)",
        "equity_model": "realized-cash (no mark-to-market; maxDD understated)",
        "max_hold_bars": int(sig.attrs.get("max_hold", 192)),
        "max_dd_pct": float(m_r["max_drawdown"]) * 100.0 if pd.notna(m_r["max_drawdown"]) else None,
    }
    if sid in (18, 20):
        m["ml_model"] = ("sklearn HistGradientBoosting (max_iter=150, "
                         "random_state=0)" if importlib.util.find_spec("sklearn")
                         else "numpy LogReg fallback (sklearn absent)")
        m["audit_note"] = ("A2: unpurged 4-bar label split in _walkforward "
                           "(inflationary, run verbatim)")
    if sid == 19:
        m["ml_model"] = "numpy 2-state HMM (EM 12 iters, seed 0)"
    if sid == 1:
        m["audit_note"] = ("A1: _levels_htf exposes the 4h pivot one 4h-bar "
                           "early (inflationary, run verbatim)")

    # ── repo cost: the verdict ────────────────────────────────────────────
    m["return_pct"] = float(eq.iloc[-1] - 1.0) * 100.0
    m["n_trades"] = int(m_r["trades"])
    m["win_rate_pct"] = float(m_r["win_rate"]) * 100.0 if pd.notna(m_r["win_rate"]) else None
    pf, noloss = _pf(tr_r["pnl"].to_numpy(float) if len(tr_r) else np.zeros(0))
    m["profit_factor"] = pf
    m["pf_no_losses"] = noloss

    # ── cost controls, measured on the SAME signals ───────────────────────
    m["zero_cost_ret_pct"] = float(zero[2]["total_return"]) * 100.0
    zpf, _ = _pf(zero[0]["pnl"].to_numpy(float) if len(zero[0]) else np.zeros(0))
    m["zero_cost_pf"] = zpf
    m["drag_pp"] = m["zero_cost_ret_pct"] - m["return_pct"]
    m["pack_cost_ret_pct"] = float(pack[2]["total_return"]) * 100.0

    # ── buy & hold, same window ───────────────────────────────────────────
    m["bh_return_pct"] = float(df["close"].iloc[-1] / df["open"].iloc[0] - 1.0) * 100.0

    if len(tr_r) == 0:
        return m, []

    # ── 70/30 split on entry time ─────────────────────────────────────────
    split_ts = df.index[int(n_bars * 0.7)]
    entry_ts = pd.to_datetime(tr_r["entry_time"])
    oos_mask = (entry_ts >= split_ts).to_numpy()
    oos_pnls = tr_r["pnl"].to_numpy(float)[oos_mask]
    opf, _ = _pf(oos_pnls)
    m["oos_profit_factor"] = opf
    m["oos_n_trades"] = int(oos_mask.sum())
    base = eq[eq.index < split_ts]
    o0 = float(base.iloc[-1]) if len(base) else 1.0
    m["oos_return_pct"] = float(eq.iloc[-1] / o0 - 1.0) * 100.0
    ins_pnls = tr_r["pnl"].to_numpy(float)[~oos_mask]
    ipf, _ = _pf(ins_pnls)
    m["ins_profit_factor"] = ipf

    # ── equal thirds (realized-cash anchors, declared) ────────────────────
    third = n_bars // 3
    greens = 0
    thirds_map = {}
    if third > 0:
        for i in range(3):
            a = float(eq.iloc[i * third])
            b = float(eq.iloc[min((i + 1) * third, n_bars - 1)])
            thirds_map[f"t{i + 1}"] = 100.0 * (b / a - 1.0)
            greens += int(b > a)
    m["n_periods_green"] = int(greens)
    m["thirds_map_pct"] = {k: round(v, 4) for k, v in thirds_map.items()}

    # ── concentration: best-5 trades ──────────────────────────────────────
    pnls = np.sort(tr_r["pnl"].to_numpy(float))[::-1]
    top5 = float(pnls[:5].sum())
    net = float(pnls.sum())
    if net > 0:
        m["best5_share_pct"] = 100.0 * top5 / net
    m["conc_net_without_top5_pct"] = 100.0 * (net - top5)   # INIT=1.0 base, declared

    # ── per-trade bootstrap CI (bps of entry cash per trade) ──────────────
    d = np.where(tr_r["dir"] == "long", 1.0, -1.0)
    rets = d * (tr_r["exit"].to_numpy(float) / tr_r["entry"].to_numpy(float) - 1.0)
    seed = int(params.get("boot_seed", BOOT_SEED_DEFAULT))
    draws = int(params.get("boot_draws", BOOT_DRAWS_DEFAULT))
    lo, hi = _boot_ci(rets, seed, draws)
    m["boot_ci_lo"] = lo
    m["boot_ci_hi"] = hi
    m["boot_ci_units"] = "bps of entry cash per trade"
    m["boot_seed"] = seed
    m["boot_draws"] = draws

    # ── yearly PnL from the trades ────────────────────────────────────────
    yr = entry_ts.dt.year
    years = {int(y): float(g["pnl"].sum()) for y, g in tr_r.groupby(yr)}

    tables = [_cost_row("repo", tr_r, eq),
              _cost_row("zero", zero[0], zero[1]),
              _cost_row("pack_default", pack[0], pack[1]),
              *[{"id": f"year_{y}", "kind": "year", "year": int(y),
                 "pnl": v} for y, v in sorted(years.items())]]
    return m, tables


def run_one(paths, params):
    p = dict(params)
    sid = p.get("id", 1)
    if isinstance(sid, str) and not sid.isdigit():
        key = sid if sid in STRATEGIES else None
        sid = KEYS.index(key) + 1
    else:
        sid = int(sid)
        if not 1 <= sid <= 20:
            raise ValueError(f"id must be 1..20, got {sid!r}")
        key = KEYS[sid - 1]
    strat_params = {k: v for k, v in p.items() if k not in RESERVED}
    df = load_df(paths[0])
    sig = STRATEGIES[key](df, strat_params or None)
    repo = P20.run_backtest(df, sig, **REPO)
    zero = P20.run_backtest(df, sig, **ZERO)
    pack = P20.run_backtest(df, sig, **PACK_DEFAULT)
    m, tables = _metrics(df, sig, repo, zero, pack, key, sid, p)
    prov = {"adapter": "pack20", "engine_version": "pack20-1",
            "source": "Downloads/strategy_pack_20.py (byte-identical copy, "
                      f"sha256 {ENGINE_SHA256[:16]}...)",
            "executor": "the pack's own run_backtest, verbatim",
            "funding": "not charged (declared)",
            "audit": "code/_pack20_audit.py ALL PASS before any real-data artifact"}
    return m, prov, tables
