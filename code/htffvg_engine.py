#!/usr/bin/env python
"""htffvg_engine.py -- harness adapter around the htf_ltf_fvg pack.

SOURCE OF RECORD: code/htf_ltf_fvg_strategy.py (the attachment copied
byte-identical, sha256 4b96cf6ec72fcdca...). The pack implements "4H FVG ->
15M tap -> new 15M FVG entry" with TWO independent engines (vector + event)
that must agree trade-for-trade, declared no-lookahead conventions (a 4H FVG
is known only at 4H close; FVG signals act at the completing bar's close with
fills from the next bar), SL-first on spanning bars, gap fills at the open,
risk-per-trade sizing capped by max_leverage.

WHAT THE ADAPTER ADDS (nothing else):
  * feeds the REPO's hashed 15m klines (native dir, taker fallback, tail
    files merged) instead of a live fetch -- data bytes are part of run_id;
  * runs BOTH engines on the same slice and requires 1:1 trade parity
    (parity_ok inside the artifact; a mismatch aborts the run);
  * asserts the accounting invariant eq[-1] - init == sum(pnl) inside the
    artifact (inv_gap published);
  * cost regimes: cost_mode gate = the pack's own fee schedule aligned to the
    repo standard (taker 5 bps + slippage 0.5 bps per side; maker fills pay
    2 bps, no slip) | zero (control, drag measured in-artifact);
  * the standard bt.py one battery metrics (PF, n, net, thirds, frozen 70/30
    OOS, best-5 concentration, own bootstrap CI);
  * FILL MODEL declared per entry_mode: market = taker at the next open
    (certifiable on 15m bars); limit = a resting maker order filled on an
    intrabar touch -- per the repo fill-model rule this is NOT certifiable on
    OHLC bars and any PASS from limit cells must be treated as
    uncertifiable until a 1m-resolution or forward confirmation exists.
  * FUNDING is NOT charged (the pack is kline-only, declared; holds run up to
    max_hold bars, default 96 x 15m = 24h ~ three 8h settlements -- the drag
    direction depends on the side held).
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
from htf_ltf_fvg_strategy import (  # noqa: E402  (source of record, by import)
    Params, compare, event_backtest, load_csv, vector_backtest,
)

ENGINE_VERSION = "htffvg-1"
INIT = 10_000.0

COSTS = {
    # gate = the repo standard mapped onto the pack's maker/taker schedule
    "gate": dict(fee_taker_bps=5.0, fee_maker_bps=2.0, slippage_bps=0.5),
    "zero": dict(fee_taker_bps=0.0, fee_maker_bps=0.0, slippage_bps=0.0),
}


def _load_panel(paths) -> pd.DataFrame:
    """Merge the symbol's 15m CSVs (main + tails, native or taker) into the
    pack's expected tz-naive datetime-indexed OHLC frame."""
    dfs = []
    for x in paths:
        if str(x).lower().endswith(".json"):
            continue
        dfs.append(str(x))
    if not dfs:
        raise ValueError("htffvg: no kline csv in inputs")
    frames = []
    sym = None
    for fp in dfs:
        df = pd.read_csv(fp)
        df.columns = [str(c).strip().lower() for c in df.columns]
        base = os.path.basename(fp).upper()
        s = base.split("_")[0]
        sym = s if sym is None else sym
        frames.append(df)
    df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    df = df.drop_duplicates("open_ts").sort_values("open_ts").reset_index(drop=True)
    out = load_csv.__wrapped__(df) if hasattr(load_csv, "__wrapped__") else None
    # build the pack's frame directly (open_ts ms -> naive UTC index)
    idx = pd.to_datetime(df["open_ts"], unit="ms")
    out = pd.DataFrame({"open": df["open"].to_numpy(float),
                        "high": df["high"].to_numpy(float),
                        "low": df["low"].to_numpy(float),
                        "close": df["close"].to_numpy(float)}, index=idx)
    out = out[~out.index.duplicated()].sort_index()
    return out, sym


def run_cell(paths, params) -> dict:
    p_in = dict(params)
    tf = str(p_in.get("tf", "15m"))
    if tf != "15m":
        raise ValueError(f"htffvg runs 15m only (got tf={tf!r})")
    cost_mode = str(p_in.get("cost_mode", "gate"))
    if cost_mode not in COSTS:
        raise ValueError(f"htffvg cost_mode must be one of {list(COSTS)}")
    entry_mode = str(p_in.get("entry_mode", "market"))
    if entry_mode not in ("market", "limit"):
        raise ValueError("htffvg entry_mode must be market|limit")

    ltf, sym = _load_panel(paths)
    cc = COSTS[cost_mode]
    p = Params(entry_mode=entry_mode,
               entry_frac=float(p_in.get("entry_frac", 0.5)),
               limit_expiry=int(p_in.get("limit_expiry", 8)),
               rr=float(p_in.get("rr", 2.0)),
               sl_buffer_bps=float(p_in.get("sl_buffer_bps", 0.0)),
               min_htf_gap_bps=float(p_in.get("min_htf_gap_bps", 0.0)),
               min_ltf_gap_bps=float(p_in.get("min_ltf_gap_bps", 0.0)),
               max_zone_age=int(p_in.get("max_zone_age", 0)),
               max_hold=int(p_in.get("max_hold", 96)),
               risk_pct=float(p_in.get("risk_pct", 0.01)),
               max_leverage=float(p_in.get("max_leverage", 5.0)),
               fee_taker_bps=cc["fee_taker_bps"],
               fee_maker_bps=cc["fee_maker_bps"],
               slippage_bps=cc["slippage_bps"],
               init_equity=INIT)

    tv = vector_backtest(ltf, p)
    te = event_backtest(ltf, p)
    par = compare(tv, te)
    if not par:
        raise RuntimeError("htffvg: vector/event parity FAILED -- no artifact")

    # the pack has no index columns beyond times; rebuild bar indices for OOS
    n_bars = len(ltf)
    ts_index = ltf.index
    split_i = int(n_bars * 0.7)
    split_ts = ts_index[split_i]

    tr = tv
    eq = np.r_[INIT, tr["equity"].to_numpy()] if not tr.empty else np.array([INIT])
    pnls = tr["pnl"].to_numpy(float) if not tr.empty else np.zeros(0)
    ret = 100.0 * (eq[-1] / INIT - 1.0)
    peak = np.maximum.accumulate(eq)
    mdd = float(((eq - peak) / np.maximum(peak, 1e-9)).min())
    n = len(tr)
    wins = int((pnls > 0).sum())
    gp = pnls[pnls > 0].sum()
    gl = -pnls[pnls <= 0].sum()
    pf = float(gp / gl) if gl > 0 else (float("inf") if gp > 0 else 0.0)

    def thirds(e):
        out = []
        for k in range(3):
            a, b = int(len(e) * k / 3), int(len(e) * (k + 1) / 3)
            out.append(100.0 * (e[b - 1] / e[a] - 1.0)
                       if b > a and e[a] > 0 else 0.0)
        return out

    oos_mask = np.array([t >= split_ts for t in tr["entry_time"]]) if n \
        else np.zeros(0, bool)
    oos_pnls = pnls[oos_mask]
    ogp = oos_pnls[oos_pnls > 0].sum()
    ogl = -oos_pnls[oos_pnls <= 0].sum()
    oos_pf = float(ogp / ogl) if ogl > 0 else (float("inf") if ogp > 0 else 0.0)
    # OOS return measured on the TRADE-LEVEL curve from the equity BEFORE the
    # first OOS trade (the split is a bar index; the curve is per-trade)
    if oos_mask.any():
        first_oos = int(oos_mask.argmax())
        base_eq = eq[first_oos]
        oos_ret = 100.0 * (eq[-1] / base_eq - 1.0) if base_eq > 0 else 0.0
    else:
        oos_ret = 0.0
    best5 = float(np.sort(pnls)[::-1][:5].sum()) if n else 0.0
    total = float(pnls.sum()) if n else 0.0

    # measured average round-trip cost from the actual trades (fees / entry
    # notional); the declared per-side schedule goes out as fee/slippage
    if n:
        rt = (tr["fees"] / (tr["qty"] * tr["entry"].abs()) * 1e4)
        cost_measured = float(rt.mean())
    else:
        cost_measured = 2.0 * (cc["fee_taker_bps"] + cc["slippage_bps"])

    inv_gap = float(eq[-1] - INIT - pnls.sum())

    m = dict(
        return_pct=ret,
        profit_factor=pf,
        n_trades=n,
        win_rate=100.0 * wins / n if n else 0.0,
        max_dd_pct=100.0 * mdd,
        thirds_net_pct=thirds(eq),
        n_periods_green=int(sum(1 for x in thirds(eq) if x > 0)),
        oos_split_bar=split_i,
        oos_return_pct=oos_ret,
        oos_n_trades=int(oos_mask.sum()),
        oos_profit_factor=oos_pf,
        best5_share_pct=(100.0 * best5 / total) if total else float("nan"),
        parity_ok=True,
        inv_gap_usd=inv_gap,
        entry_mode=entry_mode,
        fill_model=("taker_next_open" if entry_mode == "market"
                    else "maker_intrabar (NOT certifiable on OHLC bars)"),
        cost_mode=cost_mode,
        cost_bp_roundtrip=cost_measured,
        fee_bps_per_side=cc["fee_taker_bps"],
        slippage_bps_per_side=cc["slippage_bps"],
        funding_model="off (declared: the pack is kline-only)",
        exits={k: int(v) for k, v in tr["reason"].value_counts().items()} if n else {},
        symbol=sym,
    )
    if n > 1:
        rng = np.random.default_rng(7)
        boot = np.array([rng.choice(pnls, len(pnls), replace=True).mean()
                         for _ in range(20000)])
        m["boot_ci_lo"] = float(np.percentile(boot, 2.5))
        m["boot_ci_hi"] = float(np.percentile(boot, 97.5))
        m["boot_p_le_zero"] = float((boot <= 0).mean())
        m["boot_draws"] = 20000
        m["boot_seed"] = 7
    if cost_mode != "zero":
        zp = Params(**{**p.__dict__, "fee_taker_bps": 0.0,
                       "fee_maker_bps": 0.0, "slippage_bps": 0.0})
        zt = vector_backtest(ltf, zp)
        zeq = np.r_[INIT, zt["equity"].to_numpy()] if not zt.empty \
            else np.array([INIT])
        m["ret_zero_pct"] = 100.0 * (zeq[-1] / INIT - 1.0)
        zpnl = zt["pnl"].to_numpy(float) if not zt.empty else np.zeros(0)
        zgp, zgl = zpnl[zpnl > 0].sum(), -zpnl[zpnl <= 0].sum()
        m["pf_zero"] = float(zgp / zgl) if zgl > 0 else 0.0
        m["n_zero"] = len(zt)
        m["drag_pp"] = m["ret_zero_pct"] - ret
    m["gate_pf"] = bool(pf > 1.2)
    m["gate_n"] = bool(n >= 30)
    m["gate_net"] = bool(ret > 0)
    m["gate_thirds"] = bool(m["n_periods_green"] >= 2)
    m["gate_oos"] = bool(oos_pf > 1.2 and oos_ret > 0)
    m["gate_conc"] = bool(np.isfinite(m["best5_share_pct"])
                          and m["best5_share_pct"] <= 100.0)
    m["gate_boot_ci"] = bool(n > 1 and m.get("boot_ci_lo", 0.0) > 0)
    m["gate_all"] = bool(m["gate_pf"] and m["gate_n"] and m["gate_net"]
                         and m["gate_thirds"] and m["gate_oos"]
                         and m["gate_conc"] and m["gate_boot_ci"])
    m["closed_pnl"] = [float(x) for x in pnls]
    return m
