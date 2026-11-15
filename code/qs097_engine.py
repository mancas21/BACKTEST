#!/usr/bin/env python
"""qs097_engine.py -- QS-097 "Cross-asset confirmation strategy" (family J).

SOURCE OF RECORD: the catalog card (2026-11-06 user prompt), verbatim rules:

  LONG entry : Donchian(20) breakout on asset X taken ONLY IF BTC and ETH are
               above their own EMA(50) AND at least 2 of the other perps are
               above theirs.
  SHORT      : mirror (two-sided variant tested as a SEPARATE hypothesis).
  EXIT       : close below the 10-bar low, or confirmation lost.
  STOP       : 2*ATR(14).  TP: none.  Max hold: 150 bars.
  FREQUENCY  : one entry per signal EPISODE (no re-entry while the condition
               persists); cool-down 5 bars after an exit; max 1 open position
               per symbol.
  NO-TRADE   : the confirmation set contains stale data.

DECLARED READINGS (the card leaves these to the implementation):
  * EPISODE = a contiguous run of bars where the breakout STATE holds
    (close > prior-20-bar high for longs). An entry may fire only on the
    FIRST bar of a run; after an exit, re-entry needs a NEW episode (the
    state must go false at least once). The executor's one-position rule
    and G1's 5-bar cooldown layer on top.
  * CONFIRMATION, as-of and no-lookahead: at traded bar i (decided at ITS
    close), each confirm asset contributes the value of ITS OWN latest bar
    with open_ts <= traded bar's open_ts (bar i inclusive -- that bar
    closes exactly when the traded bar does). EMA(50) of that asset's own
    closes on the same timeframe.
  * STALE: a confirm asset is stale when its latest such bar is older than
    2 traded-bars (one missed bar allowed) or its EMA(50) is still NaN.
    Stale => the confirmation is NOT evaluable => entries are vetoed; the
    "confirmation lost" exit fires only on an explicit BELOW, never on
    stale (flat is safer than a vetoed exit).
  * "other perps" = {SOL, HYPE, SUI, JUP} minus the traded symbol if it
    belongs to that set (then 3 names remain); BTC/ETH are always required.
  * Confirmation set = all six names. X may be BTC or ETH itself (its own
    EMA state is then part of both the breakout and the confirmation).

EXECUTION: the catalog executor code/qs_engine.py imported BY IDENTITY --
G1 sizing (1% risk to the stop, max_gross 3x, daily-loss halt 3%, DD halve
15% / review-halt 25%, cooldown 5), G3 funding charged at real settlement
instants, stop-first intrabar with gap-through fills at the open, exits and
entries fill at the NEXT open, end-of-data force close. Costs G2: the
catalog "gate" preset = 5 bps fee + 0.5 bps slip per side = 11 bps RT (the
repo standard); a zero-cost control runs inside every artifact.

SIZING G1 means the equity curve compounds the whole book; per-symbol books
are independent (max 1 open position per symbol is inherent).
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
from qs_engine import (  # noqa: E402  (catalog primitives, BY IDENTITY)
    G1, COSTS, INIT, atr as cat_atr, ema as cat_ema, load_funding, run as cat_run,
)

ENGINE_VERSION = "qs097-1"

# the catalog's cost presets plus the zero control (qs_engine.py is
# hash-pinned by its own artifacts, so the preset is added HERE, not there)
COSTS097 = {**COSTS, "zero": dict(fee=0.0, slip=0.0, stop_slip_mult=1.0)}

UNIVERSE = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "SUIUSDT", "JUPUSDT")
REQUIRED = ("BTCUSDT", "ETHUSDT")
OTHERS = tuple(s for s in UNIVERSE if s not in REQUIRED)

P = dict(
    donchian_n=20, exit_low_n=10, ema_n=50, atr_n=14,
    atr_stop_mult=2.0, max_hold=150, min_others=2,
    stale_bars=2,                 # latest confirm bar may lag <= 2 bars
    variant="long",               # long | two_side  (separate hypotheses)
)


def _panel_state(panel: dict, traded: str, tf_ms: int, cfg: dict):
    """Per traded-bar confirmation state, as-of and no-lookahead.

    Returns (req_ok_long, req_ok_short, others_long, others_short, stale)
    as boolean/int arrays over the TRADED symbol's bars:
      req_ok_long[b]    BTC and ETH both above their EMA50 (explicitly)
      req_ok_short[b]   BTC and ETH both below their EMA50 (explicitly)
      others_long[b]    how many other perps are above their EMA50
      others_short[b]   how many are below
      stale[b]          any confirm asset's data is stale for bar b
    An explicit ABOVE/BELOW requires a fresh bar with a non-NaN EMA; a stale
    or warmup asset contributes neither above nor below, and sets stale.
    """
    t_ts = panel[traded]["open_ts"].to_numpy(np.int64)
    n = len(t_ts)
    req_ok_l = np.zeros(n, bool)
    req_ok_s = np.zeros(n, bool)
    oth_l = np.zeros(n, np.int64)
    oth_s = np.zeros(n, np.int64)
    stale = np.zeros(n, bool)

    # confirm assets = whatever the panel holds; BTC/ETH are the REQUIRED pair,
    # the rest are the "other perps" (minus the traded one)
    missing = [s for s in REQUIRED if s not in panel]
    if missing:
        raise ValueError(f"confirmation panel missing required assets {missing}")
    confirm_syms = list(panel.keys())

    # per-confirm-asset series: (ts, close, ema50) aligned to the traded bars
    states = {}
    for sym in confirm_syms:
        df = panel[sym]
        c = df["close"].to_numpy(float)
        e = cat_ema(c, cfg["ema_n"]).to_numpy(float)
        states[sym] = (df["open_ts"].to_numpy(np.int64), c, e)

    for b in range(n):
        t = t_ts[b]
        oldest_ok = t - cfg["stale_bars"] * tf_ms
        req_l = req_s = True
        oth_l_cnt = oth_s_cnt = 0
        any_stale = False
        for sym in confirm_syms:
            ts_a, c_a, e_a = states[sym]
            j = int(np.searchsorted(ts_a, t, side="right")) - 1
            if j < 0 or ts_a[j] < oldest_ok or not np.isfinite(e_a[j]):
                any_stale = True          # no fresh, warm bar => not evaluable
                if sym in REQUIRED:
                    req_l = req_s = False
                continue
            above = c_a[j] > e_a[j]
            below = c_a[j] < e_a[j]
            if sym in REQUIRED:
                req_l &= above
                req_s &= below
            elif sym != traded:
                oth_l_cnt += above
                oth_s_cnt += below
        req_ok_l[b] = req_l
        req_ok_s[b] = req_s
        oth_l[b] = oth_l_cnt
        oth_s[b] = oth_s_cnt
        stale[b] = any_stale
    return req_ok_l, req_ok_s, oth_l, oth_s, stale


def build_plan(panel: dict, traded: str, tf_ms: int, cfg: dict) -> dict:
    """QS-097 plan arrays for one traded symbol (catalog executor contract)."""
    df = panel[traded]
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    n = len(c)

    s = pd.Series
    prior_hi = s(h).shift(1).rolling(cfg["donchian_n"]).max()
    prior_lo = s(l).shift(1).rolling(cfg["donchian_n"]).min()
    exit_lo = s(l).shift(1).rolling(cfg["exit_low_n"]).min()
    a = cat_atr(h, l, c, cfg["atr_n"]).to_numpy(float)

    brk_long = (c > prior_hi.to_numpy(float))
    brk_short = (c < prior_lo.to_numpy(float))
    brk_long = np.nan_to_num(brk_long).astype(bool)
    brk_short = np.nan_to_num(brk_short).astype(bool)

    # episodes: entry only on the first bar of a True run
    new_ep_l = brk_long & ~np.roll(brk_long, 1)
    new_ep_l[0] = brk_long[0]
    new_ep_s = brk_short & ~np.roll(brk_short, 1)
    new_ep_s[0] = brk_short[0]

    req_l, req_s, oth_l, oth_s, stale = _panel_state(panel, traded, tf_ms, cfg)

    conf_l = req_l & (oth_l >= cfg["min_others"]) & ~stale
    conf_s = req_s & (oth_s >= cfg["min_others"]) & ~stale

    long_event = new_ep_l & conf_l
    short_event = (new_ep_s & conf_s) if cfg["variant"] == "two_side" \
        else np.zeros(n, bool)

    # exits: 10-bar low break, or the REQUIRED confirmation explicitly lost
    exit_lo_hit = c < exit_lo.to_numpy(float)
    conf_lost_l = ~req_l & ~stale     # explicit below on BTC or ETH; never on stale
    conf_lost_s = ~req_s & ~stale
    long_exit = np.nan_to_num(exit_lo_hit | conf_lost_l).astype(bool)
    short_exit = np.nan_to_num((c > s(h).shift(1).rolling(cfg["exit_low_n"]).max().to_numpy(float))
                               | conf_lost_s).astype(bool)

    sd = np.where(np.isfinite(a), cfg["atr_stop_mult"] * a, np.nan)
    # G5/active window: before every confirm asset has warm history the whole
    # panel is stale and the book cannot trade; metrics must be measured on
    # the ACTIVE window (the xsf lesson), so expose its first bar.
    st = np.asarray(stale, bool)
    first_active = int(np.argmax(~st)) if (~st).any() else n
    return dict(
        long_event=long_event, short_event=short_event,
        long_exit=long_exit, short_exit=short_exit,
        stop_dist_long=sd, stop_dist_short=sd,
        stop_level_long=np.full(n, np.nan),
        stop_level_short=np.full(n, np.nan),
        tp_dist=None, atr=a, max_hold=cfg["max_hold"],
        first_active=first_active,
    )


def run_symbol(panel: dict, traded: str, tf_ms: int, cfg: dict,
               funding_path=None, cost="gate", init=INIT):
    """One traded-symbol book under the catalog executor (BY IDENTITY)."""
    cc = COSTS097[cost]
    plan = build_plan(panel, traded, tf_ms, cfg)
    funding = load_funding(funding_path) if funding_path else None
    out = cat_run(panel[traded], plan, cc["fee"], cc["slip"],
                  stop_slip_mult=cc.get("stop_slip_mult", 1.0),
                  funding=funding, g1=dict(G1), init=init)
    out["first_active"] = plan["first_active"]
    out["plan_counts"] = dict(
        long_events=int(np.asarray(plan["long_event"]).sum()),
        short_events=int(np.asarray(plan["short_event"]).sum()),
        long_exits=int(np.asarray(plan["long_exit"]).sum()),
        short_exits=int(np.asarray(plan["short_exit"]).sum()),
    )
    out["cost"] = cost
    return out


def _pf(pnls):
    gp = pnls[pnls > 0].sum()
    gl = -pnls[pnls < 0].sum()
    if gl > 0:
        return float(gp / gl)
    return (float("inf") if gp > 0 else 0.0)


def _thirds(eq):
    e = np.asarray(eq, float)
    out = []
    for k in range(3):
        a, b = int(len(e) * k / 3), int(len(e) * (k + 1) / 3)
        out.append(100.0 * (e[b - 1] / e[a] - 1.0) if b > a and e[b - 1] > 0 else 0.0)
    return out


def run_symbol_metrics(panel: dict, traded: str, tf_ms: int, cfg: dict,
                       funding_path=None, cost="gate", init=INIT) -> dict:
    """Adapter contract: full metrics dict for bt.py one's standard battery."""
    out = run_symbol(panel, traded, tf_ms, cfg, funding_path, cost, init)
    eq = out["eq"]
    trades = out["trades"]
    active = int(out.get("first_active", 0))
    n_bars = len(eq)
    pnls = np.array([t["pnl"] for t in trades], float) if trades else np.zeros(0)
    ret = 100.0 * (eq[-1] / float(init) - 1.0)
    peak = np.maximum.accumulate(np.nan_to_num(eq, nan=float(init)))
    mdd = float(((np.nan_to_num(eq, nan=float(init)) - peak)
                 / np.maximum(peak, 1e-9)).min())
    n = len(trades)
    wins = sum(1 for t in trades if t["pnl"] > 0)

    ts_bar = panel[traded]["open_ts"].to_numpy(np.int64)
    # frozen 70/30 INSIDE the active window (a late-starting panel must not
    # spend its thirds and its OOS on bars the no-trade rule vetoes)
    split = active + int((n_bars - active) * 0.7)
    split_ms = int(ts_bar[split]) if len(ts_bar) else 0
    oos_mask = np.array([t["entry_ts"] >= split_ms for t in trades]) if n \
        else np.zeros(0, bool)

    m = dict(
        return_pct=ret,
        profit_factor=_pf(pnls) if n else 0.0,
        n_trades=n,
        win_rate=100.0 * wins / n if n else 0.0,
        max_dd_pct=100.0 * mdd,
        thirds_net_pct=_thirds(eq[active:]),
        n_periods_green=int(sum(1 for x in _thirds(eq[active:]) if x > 0)),
        oos_split_bar=split,
        active_start_bar=active,
        active_start_utc=str(pd.Timestamp(int(ts_bar[active]), unit="ms",
                                          tz="UTC")) if n_bars > active else "",
        active_bars=n_bars - active,
        oos_return_pct=100.0 * (eq[-1] / eq[split] - 1.0)
        if len(eq) > split + 1 and np.isfinite(eq[split]) and eq[split] > 0 else 0.0,
        oos_n_trades=int(oos_mask.sum()),
        oos_profit_factor=_pf(pnls[oos_mask]) if oos_mask.any() else 0.0,
        best5_share_pct=(100.0 * float(np.sort(pnls)[::-1][:5].sum())
                         / float(pnls.sum())) if n and pnls.sum() else float("nan"),
        n_stop_fills=out["n_stop_fills"], n_gap_fills=out["n_gap_fills"],
        n_daily_halts=out["n_daily_halts"], n_review_halt=out["n_review_halt"],
        max_leverage=out["max_leverage"],
        funding_paid=out["fund_paid"], n_funding=out["n_funding"],
        fees_paid=out["fees_paid"],
        plan_counts=out["plan_counts"],
        variant=cfg["variant"], traded=traded,
        cost_mode=cost,
        cost_bp_roundtrip=2.0 * (COSTS097[cost]["fee"] + COSTS097[cost]["slip"]) * 1e4,
        fee_bps_per_side=COSTS097[cost]["fee"] * 1e4,
        slippage_bps_per_side=COSTS097[cost]["slip"] * 1e4,
        funding_model=("real settlements" if funding_path else
                       "off (no funding file for this symbol)"),
    )
    if cost != "zero":
        zc = run_symbol(panel, traded, tf_ms, cfg, None, "zero", init)
        zpn = np.array([t["pnl"] for t in zc["trades"]], float) \
            if zc["trades"] else np.zeros(0)
        m["ret_zero_pct"] = 100.0 * (zc["eq"][-1] / float(init) - 1.0)
        m["pf_zero"] = _pf(zpn) if len(zpn) else 0.0
        m["n_zero"] = len(zc["trades"])
        m["drag_pp"] = m["ret_zero_pct"] - ret
    # own-uncertainty bootstrap (seeded, in-artifact)
    if n > 1:
        rng = np.random.default_rng(7)
        boot = np.array([rng.choice(pnls, len(pnls), replace=True).mean()
                         for _ in range(20000)])
        m["boot_ci_lo"] = float(np.percentile(boot, 2.5))
        m["boot_ci_hi"] = float(np.percentile(boot, 97.5))
        m["boot_p_le_zero"] = float((boot <= 0).mean())
        m["boot_draws"] = 20000
        m["boot_seed"] = 7
    m["gate_pf"] = bool(m["profit_factor"] > 1.2)
    m["gate_n"] = bool(m["n_trades"] >= 30)
    m["gate_net"] = bool(m["return_pct"] > 0)
    m["gate_thirds"] = bool(m["n_periods_green"] >= 2)
    m["gate_oos"] = bool(m["oos_profit_factor"] > 1.2 and m["oos_return_pct"] > 0)
    m["gate_conc"] = bool(np.isfinite(m["best5_share_pct"])
                          and m["best5_share_pct"] <= 100.0)
    m["gate_boot_ci"] = bool(n > 1 and m.get("boot_ci_lo", 0.0) > 0)
    m["gate_all"] = bool(m["gate_pf"] and m["gate_n"] and m["gate_net"]
                         and m["gate_thirds"] and m["gate_oos"]
                         and m["gate_conc"] and m["gate_boot_ci"])
    m["closed_pnl"] = [float(x) for x in pnls]
    return m


# ── harness entry ───────────────────────────────────────────────────────────
TF_MS = {"15m": 15 * 60_000, "1h": 3_600_000}


def run_cell(paths, params):
    """`paths` = the six kline CSVs (+ funding file for the traded symbol last).
    `params['symbol']` selects the traded book; `params['tf']` in {15m,1h};
    `params['variant']` in {long, two_side}; `params['cost']` in
    {gate, base, adverse, stress, zero} (verdict cost = gate)."""
    p = dict(P)
    p.update({k: v for k, v in params.items() if v is not None})
    traded = str(p.get("card") or p.get("symbol") or "").upper()
    tf = str(p.get("tf", "1h"))
    if tf not in TF_MS:
        raise ValueError(f"qs097 supports 15m/1h only (got tf={tf!r})")
    if traded not in UNIVERSE:
        raise ValueError(f"qs097 traded symbol must be one of {UNIVERSE} "
                         f"(got {traded!r})")

    groups = {}
    funding_path = None
    for x in paths:
        base = os.path.basename(str(x)).upper()
        if base.endswith(".JSON"):
            funding_path = str(x)
            continue
        sym = base.split("_")[0]        # basename already carries USDT
        groups.setdefault(sym, []).append(str(x))
    panel = {}
    for sym, fs in groups.items():
        dfs = []
        for fp in fs:
            df = pd.read_csv(fp)
            df.columns = [str(cc).strip().lower() for cc in df.columns]
            dfs.append(df)
        df = pd.concat(dfs, ignore_index=True) if len(dfs) > 1 else dfs[0]
        df = df.drop_duplicates("open_ts").sort_values("open_ts").reset_index(drop=True)
        panel[sym] = df
    missing = [s for s in UNIVERSE if s not in panel]
    if missing:
        raise ValueError(f"qs097 panel incomplete, missing {missing}")

    return run_symbol_metrics(panel, traded, TF_MS[tf], p,
                              funding_path=funding_path,
                              cost=str(p.get("cost", "gate")))
