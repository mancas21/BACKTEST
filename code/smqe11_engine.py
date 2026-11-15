#!/usr/bin/env python
"""smqe11_engine.py — SMQE v1.1 (indicator merge, audit-patched build) port.

SOURCE OF RECORD: code/smqe_v1_1_strategy.pine (the attachment copied
byte-identical; sha256 bf19d04c8f2687b63008313e72269a1deb0756f9bc90693e3be92e
f524833f5c). v1.1 is the single-indicator merge whose BASELINE signal is the
validated CVRMD core with every confluence gate shipped OFF (the Pine itself
declares the gates heuristic and NOT covered by the validated backtest — they
are not ported, matching the shipped defaults).

SIGNAL CORE = the v2 engine's AUDITED primitives, imported BY IDENTITY
(code/smqe_engine.py: ema_pine / rma_pine / true_range / atr_pine / rsi_pine /
session_vwap / _divergence — 40/40 known answers before any real-data run),
combined exactly as v1.1 fuses them:
    longOK  = bullDiv AND nearLowBand AND cvdBull AND rsiLongOK
    shortOK = bearDiv AND nearHighBand AND cvdBear AND rsiShortOK
with stop_d = atr(14) x 1.5 — v1.1 has NO min-stop floor (that was the v2
strategy build).

EXECUTION SIMULATOR, verbatim from the Pine (lines 1182-1349):
  * fill at the SIGNAL bar's close (entry, TP1/TP2/stop/flip exits next bars);
  * stop = frozen stop_d; intrabar order per --fill-mode: stop-first (the
    shipped pessimistic default), tp-first, or the TV emulator path
    (O->H->L->C when (high-open) < (open-low), else O->L->H->C);
  * TP1 = VWAP mean only when favourable AND strictly inside TP2, else
    entry +/- stop_d x tp1R (1.5) — half the position; TP2 = 2R on the rest;
  * opposite signal closes the remainder at that bar's close AND reverses on
    the same bar; no same-bar re-entry after an intrabar stop or TP2;
  * cooldown (3 bars) gates entries AND flips, measured from lastEntryBar;
  * commission charged on EVERY fill and included in the trade's P&L
    (posRealized starts at -entryFee — patch H1);
  * optional slippage on market-type fills only (entry, stop, flip); TPs are
    limit-style (no slip) — the shipped default is 0;
  * funding: the Pine's own model (funding_pct8h per 8h, accrued per bar on
    the open notional prorated tfSec/28800; default 0). cost_mode=repo plus
    funding="real" additionally charges the REAL settlement instants and
    rates from data/binance_funding (adapter extension, cbpackf convention —
    declared in provenance, never mixed with the as-shipped numbers);
  * mark-to-market drawdown (open position valued at the close and at the
    adverse intrabar extreme; on the entry bar the close is used because the
    extreme preceded the fill);
  * sizing mult = min(riskPct/100/stopFrac, maxLev), stopFrac = stopD/entryPx.

COSTS: cost_mode pine = 0.06%/side commission + 0 slip (the Pine ships this);
repo = 5 bps fee + 0.5 bps slip per side (11 bps RT, the repo standard);
zero = the control, measured inside every artifact (drag_pp is measured, not
derived).

KNOWN-ANSWER AUDIT: code/_smqe11_audit.py — synthetic-bar cases for every
execution rule, primitive identity with the v2 engine, determinism,
no-lookahead truncation, zero-cost parity — ALL PASS required BEFORE any
real-data artifact. Expectation bugs count against the test first (the
audited lesson: three of three audit failures were the test's fault).
"""
from __future__ import annotations

import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = HERE
INIT = 10_000.0

# validated primitives, imported BY IDENTITY (hash-locked by the artifacts)
from smqe_engine import (  # noqa: E402
    ema_pine, rma_pine, true_range, atr_pine, rsi_pine, session_vwap,
    _divergence,
)

ENGINE_VERSION = "smqe11-1"

PINE_DEFAULTS = dict(
    cvd_smooth=3, cvd_slope_len=5, band_mult=1.0,
    rsi_len=14, rsi_os=30.0, rsi_ob=70.0,
    macd_fast=12, macd_slow=26, macd_sig=9,
    piv_l=3, piv_r=3, min_div_bars=5, max_div_bars=60,
    risk_pct=1.0, max_lev=3.0, atr_len=14, atr_mult=1.5,
    tp1_r=1.5, tp2_r=2.0, cooldown=3,
    fill_mode="stop",           # stop | tp | emu
    funding_pct8h=0.0,          # the Pine's own model, off by default
    funding="off",              # off | real (real settlement instants)
    cost_mode="repo",           # repo | pine | zero
    init=INIT,
)
COSTS = {"repo": dict(comm_pct=0.05, slip_pct=0.005),   # 5 bps + 0.5 bps / side
         "pine": dict(comm_pct=0.06, slip_pct=0.0),     # the shipped baseline
         "zero": dict(comm_pct=0.0, slip_pct=0.0)}


# ------------------------------------------------------------- signals
def signals11(t, h, l, c, v, P):
    """The v1.1 fusion with every confluence gate at its shipped OFF value.
    stop_d has NO floor (that was the v2 strategy build, not v1.1)."""
    n = len(c)
    hl_r = np.maximum(h - l, 1e-7)
    clv = ((c - l) - (h - c)) / hl_r
    d_proxy = clv * np.nan_to_num(v, nan=0.0)
    cvd_cum = np.cumsum(d_proxy)
    cvd_sm = ema_pine(cvd_cum, P["cvd_smooth"])
    k = P["cvd_slope_len"]
    slope = np.zeros(n)
    slope[k:] = cvd_sm[k:] - cvd_sm[:-k]
    cvd_bull = slope > 0
    cvd_bear = slope < 0

    vwap, vsd, _ina, ready = session_vwap(t, h, l, c, v)
    b = P["band_mult"]
    vb_l = vwap - vsd * b
    vb_u = vwap + vsd * b
    with np.errstate(invalid="ignore"):
        near_low = ready & (l <= vb_l) & (vb_l < c)
        near_high = ready & (h >= vb_u) & (c < vb_u)

    rsi = rsi_pine(c, P["rsi_len"])
    rsi_prev = np.roll(rsi, 1)
    rsi_prev[0] = np.nan
    with np.errstate(invalid="ignore"):
        rsi_long_ok = (rsi <= P["rsi_os"] + 5.0) | ((rsi < 50.0) & (rsi > rsi_prev))
        rsi_short_ok = (rsi >= P["rsi_ob"] - 5.0) | ((rsi > 50.0) & (rsi < rsi_prev))

    macd_line = ema_pine(c, P["macd_fast"]) - ema_pine(c, P["macd_slow"])
    macd_sig = ema_pine(macd_line, P["macd_sig"])
    osc = macd_line - macd_sig

    bull_div, bear_div, n_pl, n_ph = _divergence(h, l, osc, P)

    long_ok = bull_div & near_low & cvd_bull & rsi_long_ok
    short_ok = bear_div & near_high & cvd_bear & rsi_short_ok

    atr_x = atr_pine(h, l, c, P["atr_len"])
    stop_d = atr_x * P["atr_mult"]

    return dict(long_ok=long_ok, short_ok=short_ok, vwap=vwap, stop_d=stop_d,
                atr_x=atr_x, cvd_bull=cvd_bull, cvd_bear=cvd_bear,
                near_low=near_low, near_high=near_high,
                rsi_long_ok=rsi_long_ok, rsi_short_ok=rsi_short_ok,
                bull_div=bull_div, bear_div=bear_div, osc=osc, rsi=rsi,
                n_piv_l=n_pl, n_piv_h=n_ph)


# ------------------------------------------------------------- executor
def execute(t, o, h, l, c, S, P, comm_pct, slip_pct,
            fund_rate=None, fund_ts=None, tf_sec=3600):
    """The v1.1 simulator, bar by bar, in the Pine's exact order:
    manage open position -> entries from flat -> mark-to-market DD."""
    n = len(c)
    fill = P["fill_mode"]
    risk_pct, max_lev = P["risk_pct"], P["max_lev"]
    tp1_r, tp2_r, cooldown = P["tp1_r"], P["tp2_r"], P["cooldown"]
    funding_pct8h = float(P["funding_pct8h"])

    long_ok, short_ok, stop_d = S["long_ok"], S["short_ok"], S["stop_d"]
    vwap = S["vwap"]

    sim_dir = 0
    sim_entry = sim_stop_dist = sim_tp1 = sim_tp2 = sim_qty = np.nan
    sim_remain = 0.0
    sim_tp1_done = False
    pos_risk = 0.0
    pos_realized = 0.0
    last_entry_bar = -10**6
    open_entry_i = -1

    equity = float(P.get("init", INIT))
    peak = equity
    max_dd = 0.0
    total_trades = wins = 0
    gross_profit = gross_loss = sum_r = 0.0

    eq_curve = np.full(n, np.nan)
    trades = []
    fund_ptr = 0
    n_fund_events = 0
    funding_paid = 0.0
    n_stop = n_tp1 = n_tp2 = n_flip = 0

    fund_rate = np.asarray(fund_rate) if fund_rate is not None else None

    for i in range(n):
        exit_stop_bar = exit_tp1_bar = exit_tp2_bar = exit_flip_bar = False
        exec_long_bar = exec_short_bar = False
        dir_at_open = sim_dir
        emu_high_first = (h[i] - o[i]) < (o[i] - l[i])

        # ── 1) manage the position carried in ────────────────────────────
        if sim_dir != 0 and np.isfinite(sim_qty) and sim_qty > 0:
            d = sim_dir
            stop_px = sim_entry - d * sim_stop_dist
            stop_fill = stop_px * (1.0 - d * slip_pct / 100.0)
            stop_hit = low_hit = (l[i] <= stop_px) if d == 1 else (h[i] >= stop_px)
            tp1_hit = (not sim_tp1_done) and ((h[i] >= sim_tp1) if d == 1 else (l[i] <= sim_tp1))
            tp2_hit = (h[i] >= sim_tp2) if d == 1 else (l[i] <= sim_tp2)
            stop_first = bool(stop_hit) and (
                fill == "stop"
                or (fill == "emu" and ((d == 1 and not emu_high_first)
                                       or (d == -1 and emu_high_first))))

            if tp1_hit and not stop_first:
                q1 = sim_qty * 0.5
                pnl1 = d * (sim_tp1 - sim_entry) * q1
                cost1 = sim_tp1 * q1 * comm_pct / 100.0
                pos_realized += pnl1 - cost1
                equity += pnl1 - cost1
                sim_remain -= 0.5
                sim_tp1_done = True
                exit_tp1_bar = True
                n_tp1 += 1
            if tp2_hit and not stop_first and sim_remain > 0:
                q2 = sim_qty * sim_remain
                pnl2 = d * (sim_tp2 - sim_entry) * q2
                cost2 = sim_tp2 * q2 * comm_pct / 100.0
                pos_realized += pnl2 - cost2
                equity += pnl2 - cost2
                sim_remain = 0.0
                exit_tp2_bar = True
                n_tp2 += 1
            if stop_hit and sim_remain > 0:
                qs = sim_qty * sim_remain
                pnls = d * (stop_fill - sim_entry) * qs
                costs = stop_fill * qs * comm_pct / 100.0
                pos_realized += pnls - costs
                equity += pnls - costs
                sim_remain = 0.0
                exit_stop_bar = True
                n_stop += 1
            flip_sig = bool(short_ok[i]) if d == 1 else bool(long_ok[i])
            if sim_remain > 0 and flip_sig and (i - last_entry_bar >= cooldown):
                flip_fill = c[i] * (1.0 - d * slip_pct / 100.0)
                qf = sim_qty * sim_remain
                pnlf = d * (flip_fill - sim_entry) * qf
                costf = flip_fill * qf * comm_pct / 100.0
                pos_realized += pnlf - costf
                equity += pnlf - costf
                sim_remain = 0.0
                exit_flip_bar = True
                n_flip += 1

            if sim_remain <= 0:
                total_trades += 1
                sum_r += pos_realized / pos_risk if pos_risk > 0 else 0.0
                trades.append(dict(entry_i=open_entry_i, exit_i=i, dir=d,
                                   pnl=pos_realized, r=pos_realized / pos_risk
                                   if pos_risk > 0 else 0.0,
                                   reason=("stop" if exit_stop_bar else
                                           "tp2" if exit_tp2_bar else
                                           "flip" if exit_flip_bar else "tp1")))
                if pos_realized > 0:
                    wins += 1
                    gross_profit += pos_realized
                else:
                    gross_loss += abs(pos_realized)
                sim_dir = 0
            elif funding_pct8h != 0.0:
                fund = d * c[i] * sim_qty * sim_remain * funding_pct8h / 100.0 \
                    * (tf_sec / 28800.0)
                equity -= fund
                pos_realized -= fund
                funding_paid += fund
            # real settlement instants (adapter extension, cbpackf convention)
            elif fund_rate is not None:
                while fund_ptr < len(fund_rate) and fund_ts[fund_ptr] <= t[i]:
                    r = float(fund_rate[fund_ptr])
                    fund = d * c[i] * sim_qty * sim_remain * r
                    equity -= fund
                    pos_realized -= fund
                    funding_paid += fund
                    n_fund_events += 1
                    fund_ptr += 1

        # ── 2) entries from flat, at the signal bar's close ──────────────
        closed_intrabar = exit_stop_bar or exit_tp2_bar
        if sim_dir == 0 and not closed_intrabar and np.isfinite(stop_d[i]) and stop_d[i] > 0:
            cool_ok = (i - last_entry_bar) >= cooldown
            go_long = bool(long_ok[i]) and cool_ok and not (exit_flip_bar and dir_at_open == 1)
            go_short = (not go_long) and bool(short_ok[i]) and cool_ok \
                and not (exit_flip_bar and dir_at_open == -1)
            if go_long or go_short:
                d = 1 if go_long else -1
                entry_px = c[i] * (1.0 + d * slip_pct / 100.0)
                sd = float(stop_d[i])
                sim_dir = d
                sim_entry = entry_px
                sim_stop_dist = sd
                tp2_px = entry_px + d * sd * tp2_r
                vwap_ok = np.isfinite(vwap[i]) and (
                    (vwap[i] > entry_px and vwap[i] < tp2_px) if d == 1
                    else (vwap[i] < entry_px and vwap[i] > tp2_px))
                sim_tp1 = vwap[i] if vwap_ok else entry_px + d * sd * tp1_r
                sim_tp2 = tp2_px
                sim_remain = 1.0
                sim_tp1_done = False
                stop_frac = sd / entry_px
                mult = min(risk_pct / 100.0 / stop_frac, max_lev)
                sim_qty = equity * mult / entry_px
                pos_risk = sd * sim_qty
                entry_fee = entry_px * sim_qty * comm_pct / 100.0
                pos_realized = -entry_fee
                equity -= entry_fee
                last_entry_bar = i
                open_entry_i = i
                exec_long_bar = d == 1
                exec_short_bar = d == -1

        # ── 3) mark-to-market drawdown ───────────────────────────────────
        open_pnl_close = open_pnl_worst = 0.0
        if sim_dir != 0 and np.isfinite(sim_qty) and sim_remain > 0:
            q_open = sim_qty * sim_remain
            adverse = c[i] if (exec_long_bar or exec_short_bar) else \
                (l[i] if sim_dir == 1 else h[i])
            open_pnl_close = sim_dir * (c[i] - sim_entry) * q_open
            open_pnl_worst = sim_dir * (adverse - sim_entry) * q_open
        eq_close = equity + open_pnl_close
        eq_worst = equity + open_pnl_worst
        if peak > 0:
            max_dd = max(max_dd, (peak - min(eq_close, eq_worst)) / peak)
        peak = max(peak, eq_close)
        eq_curve[i] = eq_close

    # end of data: force-close any open remainder at the last close (cbpack
    # convention, counted as a closed trade)
    if sim_dir != 0 and np.isfinite(sim_qty) and sim_remain > 0:
        d = sim_dir
        exit_fill = c[-1] * (1.0 - d * slip_pct / 100.0)
        qs = sim_qty * sim_remain
        pnl = d * (exit_fill - sim_entry) * qs - exit_fill * qs * comm_pct / 100.0
        pos_realized += pnl
        equity += pnl
        total_trades += 1
        sum_r += pos_realized / pos_risk if pos_risk > 0 else 0.0
        trades.append(dict(entry_i=open_entry_i, exit_i=n - 1, dir=d,
                           pnl=pos_realized,
                           r=pos_realized / pos_risk if pos_risk > 0 else 0.0,
                           reason="end_of_data"))
        if pos_realized > 0:
            wins += 1
            gross_profit += pos_realized
        else:
            gross_loss += abs(pos_realized)
        eq_curve[-1] = equity

    # clean the trades list: drop the open-marker rows, keep closed ones
    closed = [tr for tr in trades if tr["exit_i"] >= 0]
    # entry_i of force-closed trades is unknown per-bar; keep -1 declared
    return dict(eq=eq_curve, trades=closed,
                totals=dict(equity=equity, total_trades=total_trades, wins=wins,
                            gross_profit=gross_profit, gross_loss=gross_loss,
                            sum_r=sum_r, max_dd=max_dd,
                            funding_paid=funding_paid,
                            n_fund_events=n_fund_events,
                            n_stop=n_stop, n_tp1=n_tp1, n_tp2=n_tp2,
                            n_flip=n_flip))


# ------------------------------------------------------------- metrics
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


def run_symbol(paths, params):
    p = dict(PINE_DEFAULTS)
    p.update({k: v for k, v in params.items() if v is not None})
    cost = COSTS[p["cost_mode"]]

    dfs = []
    for x in paths:
        if str(x).endswith(".json"):
            continue
        df = __import__("pandas").read_csv(x)
        df.columns = [str(x_).strip().lower() for x_ in df.columns]
        dfs.append(df)
    import pandas as pd
    df = pd.concat(dfs, ignore_index=True) if len(dfs) > 1 else dfs[0]
    df = df.drop_duplicates("open_ts").sort_values("open_ts").reset_index(drop=True)
    t = df["open_ts"].to_numpy(dtype=np.int64)
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)

    sim_start = p.get("sim_start")
    sim_end = p.get("sim_end")
    if sim_start:
        t0 = pd.Timestamp(sim_start, tz="UTC").value // 10**6
        m = t >= t0
        t, o, h, l, c, v = (a[m] for a in (t, o, h, l, c, v))
    if sim_end:
        t1 = pd.Timestamp(sim_end, tz="UTC").value // 10**6
        m = t < t1
        t, o, h, l, c, v = (a[m] for a in (t, o, h, l, c, v))

    S = signals11(t, h, l, c, v, p)

    fund_rate = fund_ts = None
    if p["funding"] == "real":
        fpath = next((x for x in paths if str(x).endswith(".json")), None)
        if fpath:
            recs = json.load(open(fpath, encoding="utf-8"))
            fts = [int(x["t"]) for x in recs]
            fund_ts = np.array(sorted(fts), dtype=np.int64)
            fund_rate = np.array([float(x["r"]) for x in
                                  sorted(recs, key=lambda x: int(x["t"]))])

    out = execute(t, o, h, l, c, S, p, cost["comm_pct"], cost["slip_pct"],
                  fund_rate=fund_rate, fund_ts=fund_ts, tf_sec=3600)
    eq = out["eq"]
    tr = out["trades"]
    tot = out["totals"]
    pnls = np.array([x["pnl"] for x in tr], float) if tr else np.zeros(0)

    bh = 100.0 * (c[-1] / c[0] - 1.0)
    ret = 100.0 * (eq[-1] / float(p.get("init", INIT)) - 1.0)
    n = len(tr)
    wr = 100.0 * tot["wins"] / tot["total_trades"] if tot["total_trades"] else 0.0
    best5 = float(np.sort(pnls)[::-1][:5].sum()) if n else 0.0
    total = float(pnls.sum()) if n else 0.0

    # frozen 70/30 split by bars (the screen's convention)
    split = int(len(c) * 0.7)
    split_ms = int(t[split]) if len(t) else 0
    oos_mask = np.array([x["exit_i"] >= split for x in tr]) if n else np.zeros(0, bool)

    m = {
        "return_pct": ret,
        "profit_factor": _pf(pnls) if n else 0.0,
        "n_trades": int(tot["total_trades"]),
        "win_rate": wr,
        "expectancy_r": tot["sum_r"] / tot["total_trades"] if tot["total_trades"] else 0.0,
        "max_dd_pct": 100.0 * tot["max_dd"],
        "bh_return_pct": bh,
        "excess_pp": ret - bh,
        "thirds_net_pct": _thirds(eq),
        "n_periods_green": int(sum(1 for x in _thirds(eq) if x > 0)),
        "oos_split_bar": split,
        "oos_return_pct": 100.0 * (eq[-1] / eq[split] - 1.0) if len(eq) > split + 1 else 0.0,
        "oos_n_trades": int(oos_mask.sum()),
        "oos_profit_factor": _pf(pnls[oos_mask]) if oos_mask.any() else 0.0,
        "bh_oos_pct": 100.0 * (c[-1] / c[split] - 1.0) if len(c) > split + 1 else 0.0,
        "best5_share_pct": (100.0 * best5 / total) if total else float("nan"),
        "net_without_best5_pct": 100.0 * (total - best5) / float(p.get("init", INIT)),
        "n_stop": tot["n_stop"], "n_tp1": tot["n_tp1"], "n_tp2": tot["n_tp2"],
        "n_flip": tot["n_flip"],
        "funding_paid": tot["funding_paid"],
        "n_funding_events": tot["n_fund_events"],
        "funding_model": ("real settlements" if fund_rate is not None else
                          ("pine prorated" if p["funding_pct8h"] else "off (declared)")),
        "cost_mode": p["cost_mode"],
        "cost_bp_roundtrip": 2.0 * (cost["comm_pct"] * 100.0 + cost["slip_pct"] * 100.0),
        "fill_mode": p["fill_mode"],
        "equity_final": eq[-1],
        "bars": int(len(c)),
        # per-trade PnL series, in-artifact for the scorecard's bootstrap and
        # Ljung-Box (quant_metrics reads metrics["closed_pnl"])
        "closed_pnl": [float(x) for x in pnls],
    }
    # significance, measured inside the artifact (a report may cite it; the
    # same seeded stream as the xrpneutral adapter: rng(7), twenty thousand
    # draws, so the scorecard and the artifact quote one interval)
    if n > 1:
        rng = np.random.default_rng(7)
        boot = np.array([rng.choice(pnls, len(pnls), replace=True).mean()
                         for _ in range(20000)])
        m["boot_ci_lo"] = float(np.percentile(boot, 2.5))
        m["boot_ci_hi"] = float(np.percentile(boot, 97.5))
        m["boot_t"] = (float(pnls.mean() / (pnls.std(ddof=1) / np.sqrt(len(pnls))))
                       if len(pnls) > 2 and pnls.std(ddof=1) > 0 else float("nan"))
        m["boot_p_le_zero"] = float((boot <= 0).mean())
        m["boot_draws"] = 20000
        m["boot_seed"] = 7
    m["gate_boot_ci"] = bool(n > 1 and m["boot_ci_lo"] > 0)
    # zero-cost control measured inside the artifact (never derived)
    if p["cost_mode"] != "zero":
        zc = COSTS["zero"]
        out0 = execute(t, o, h, l, c, S, p, zc["comm_pct"], zc["slip_pct"],
                       fund_rate=None, fund_ts=None, tf_sec=3600)
        m["ret_zero_pct"] = 100.0 * (out0["eq"][-1] / float(p.get("init", INIT)) - 1.0)
        m["pf_zero"] = _pf(np.array([x["pnl"] for x in out0["trades"]])
                           if out0["trades"] else np.zeros(0))
        m["n_zero"] = out0["totals"]["total_trades"]
        m["drag_pp"] = m["ret_zero_pct"] - ret

    # gate booleans, repo standard
    m["gate_pf"] = bool(m["profit_factor"] > 1.2)
    m["gate_n"] = bool(m["n_trades"] >= 30)
    m["gate_net"] = bool(m["return_pct"] > 0)
    m["gate_thirds"] = bool(m["n_periods_green"] >= 2)
    m["gate_oos"] = bool(m["oos_profit_factor"] > 1.2 and m["oos_return_pct"] > 0)
    m["gate_conc"] = bool(m["best5_share_pct"] <= 100.0) if np.isfinite(m["best5_share_pct"]) else False
    m["gate_all"] = bool(m["gate_pf"] and m["gate_n"] and m["gate_net"]
                         and m["gate_thirds"] and m["gate_oos"] and m["gate_conc"]
                         and m.get("gate_boot_ci", False))

    tables = [
        dict(kind="cost", id=p["cost_mode"], ret_pct=ret, pf=m["profit_factor"],
             n=n, wr_pct=wr, maxDD_pct=m["max_dd_pct"],
             drag_pp=m.get("drag_pp")),
        dict(kind="exits", id="exits", stop=tot["n_stop"], tp1=tot["n_tp1"],
             tp2=tot["n_tp2"], flip=tot["n_flip"]),
    ]
    prov = {"adapter": "smqe11", "engine_version": ENGINE_VERSION,
            "source_of_record": "code/smqe_v1_1_strategy.pine",
            "confluence_gates": "all OFF (shipped baseline)",
            "funding": m["funding_model"]}
    return m, prov, tables
