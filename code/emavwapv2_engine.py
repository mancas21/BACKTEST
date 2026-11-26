#!/usr/bin/env python
"""EMA×VWAP Suite 2 (#101–150) — harness runner.

Source: `Downloads/EMA×VWAP Suite 2 (#101–150)-claude.md` (natural-language
spec). Same skeleton as Suite 1; each row changes only what its table says.
One artifact = one row on BTCUSDT (rows 148/149 are the declared
cross-sectional exceptions). Grid and gates are frozen in
results/emavwapv2_pre_registration.md. Audit: code/_emavwapv2_audit.py.

Primitives are imported from the audited Suite 1 engine E1; this file only
adds the new entry/exit/management rules and the 3m resampling.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

import emavwap50_engine as E1

INIT = E1.INIT
REPO = dict(fee=5.0, slip=0.5)
LIMIT = dict(fee=2.0, slip=0.0)

ROWS2 = {
    0: "1h",   # internal unmodified-base control, never a campaign cell
    101: "3m", 102: "3m", 103: "3m", 104: "5m", 105: "5m", 106: "5m",
    107: "15m", 108: "15m", 109: "1h", 110: "3m",
    111: "3m", 112: "3m", 113: "5m", 114: "5m", 115: "5m", 116: "15m",
    117: "15m", 118: "15m", 119: "1h", 120: "1h",
    121: "3m", 122: "5m", 123: "15m", 124: "1h", 125: "5m", 126: "15m",
    127: "15m", 128: "1h",
    129: "3m", 130: "5m", 131: "5m", 132: "15m", 133: "15m", 134: "1h",
    135: "3m", 136: "3m", 137: "5m", 138: "5m", 139: "15m", 140: "1h",
    141: "3m", 142: "3m", 143: "5m", 144: "5m", 145: "5m", 146: "15m",
    147: "15m", 148: "15m", 149: "1h", 150: "1h",
}
XROWS = {148: ("X15", "15m"), 149: ("X1H", "1h")}
RESAMPLED = {101, 102, 103, 110, 111, 112, 121, 129, 135, 136, 141, 142}


def resample_3m(df):
    d = df.copy()
    g = (d["open_ts"].to_numpy(np.int64) // 180_000)
    out = d.groupby(g).agg(open_ts=("open_ts", "first"), open=("open", "first"),
                           high=("high", "max"), low=("low", "min"),
                           close=("close", "last"), volume=("volume", "sum"))
    cols = ["taker_buy_base", "taker_buy_quote", "n_trades"]
    for c in cols:
        if c in d.columns:
            out[c] = d.groupby(g)[c].sum()
    return out.reset_index(drop=True)


def _load(path):
    df = pd.read_csv(path)
    df = df.sort_values("open_ts").reset_index(drop=True)
    return df


# ── sigma-banded VWAP ──────────────────────────────────────────────────────
def vwap_sigma(df, weekly=False, funding=False, warmup=15):
    tp = (df["high"].to_numpy(float) + df["low"].to_numpy(float) +
          df["close"].to_numpy(float)) / 3.0
    v = df["volume"].to_numpy(float)
    ts = df["open_ts"].to_numpy(np.int64)
    dt = pd.to_datetime(ts, unit="ms", utc=True)
    if funding:
        h = ((dt.hour // 8) * 8).to_numpy()
        key = dt.strftime("%Y-%m-%d") + "_" + h.astype(str)
    elif weekly:
        key = dt.strftime("%G-W%V")
    else:
        key = dt.strftime("%Y-%m-%d")
    vw = np.full(len(df), np.nan)
    sd = np.full(len(df), np.nan)
    pv = tv = pv2 = 0.0
    last, k = None, 0
    for i in range(len(df)):
        if key[i] != last:
            pv = tv = pv2 = 0.0
            k = 0
            last = key[i]
        pv += tp[i] * v[i]
        tv += v[i]
        k += 1
        if tv > 0:
            m = pv / tv
            pv2 += v[i] * (tp[i] - m) ** 2
            vw[i] = m
            if k > warmup:
                sd[i] = np.sqrt(pv2 / tv)
    return vw, sd


# ── signals ────────────────────────────────────────────────────────────────
def build(df, row):
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    n = len(df)
    tf = ROWS2[row]
    weekly = row in (119, 134, 139)
    vw, sg = vwap_sigma(df, weekly=weekly, funding=(row == 120))
    if np.isnan(vw).all():
        raise RuntimeError(f"row {row}: VWAP never warmed up")
    fast = E1.ema(c, 11)
    a = E1.atr(h, l, c, 14)
    up = np.zeros(n, bool)
    dn = np.zeros(n, bool)
    xl = np.zeros(n, bool)
    xs = np.zeros(n, bool)
    cross_up = (fast > vw) & (np.concatenate([[fast[0]], fast[:-1]]) <=
                              np.concatenate([[vw[0]], vw[:-1]]))
    cross_dn = (fast < vw) & (np.concatenate([[fast[0]], fast[:-1]]) >=
                              np.concatenate([[vw[0]], vw[:-1]]))
    cross_up[0] = cross_dn[0] = False
    armed = np.zeros(n, bool)
    for i in range(n):
        if cross_up[i] or cross_dn[i]:
            armed[i:i + 6] = True
    up = armed & (c > np.maximum(fast, vw))
    dn = armed & (c < np.minimum(fast, vw))
    xl = (c < fast) & (np.concatenate([[c[0]], c[:-1]]) >=
                       np.concatenate([[fast[0]], fast[:-1]]))
    xs = (c > fast) & (np.concatenate([[c[0]], c[:-1]]) <=
                       np.concatenate([[fast[0]], fast[:-1]]))
    extra = dict(stop=None, target=None, time_stop=None, limit=None,
                 one_leg=None, cooldown=0, pyramid=False, selector=False,
                 missed=0)
    dt = pd.to_datetime(df["open_ts"].to_numpy(np.int64), unit="ms", utc=True)

    # entry mechanics
    if row == 101:
        ok = (c > fast) & (np.concatenate([[c[0]], c[:-1]]) >
                           np.concatenate([[fast[0]], fast[:-1]]))
        up &= ok
        dn &= (c < fast) & (np.concatenate([[c[0]], c[:-1]]) <
                            np.concatenate([[fast[0]], fast[:-1]]))
    if row == 102:
        fresh = np.zeros(n, bool)
        for i in range(n):
            j = i
            while j >= 0 and i - j < 3:
                if cross_up[j]:
                    fresh[i] = True
                    break
                j -= 1
        up &= fresh
        dn &= fresh
    if row == 103:
        extra["stop_entry"] = True
    if row == 104:
        extra["limit"] = "ema"
        extra["limit_bars"] = 6
    if row == 105:
        ok = np.abs(fast - np.concatenate([[fast[0]] * 3, fast[:-3]])) >= 0.0005 * c
        up &= ok
        dn &= ok
    if row == 106:
        rng = np.maximum(h - l, 1e-12)
        body = np.abs(c - o)
        pos = (c - l) / rng
        up &= (body >= 0.6 * rng) & (pos >= 0.75)
        dn &= (body >= 0.6 * rng) & (pos <= 0.25)
    if row == 107:
        up &= (h - l) <= 2.0 * a
        dn &= (h - l) <= 2.0 * a
    if row == 108:
        gap = np.abs(fast - vw)
        ok = (gap >= 0.1 * a) & (gap <= 1.0 * a)
        up &= ok
        dn &= ok
    if row == 109:
        below = (c < vw)
        cnt = pd.Series(below).rolling(12, min_periods=12).sum().to_numpy()
        shift = np.concatenate([np.zeros(1, bool), cnt[:-1] >= 8])
        up &= shift
        dn &= np.concatenate([np.zeros(1, bool),
                              pd.Series(~below).rolling(12, min_periods=12).sum().to_numpy()[:-1] >= 8])
    if row == 110:
        extra["cooldown"] = 6

    # sigma bands / distance
    if row == 111:
        up &= c > vw + 0.5 * sg
        dn &= c < vw - 0.5 * sg
    if row == 112:
        up &= c > vw + sg
        dn &= c < vw - sg
    if row == 113:
        ok = c <= vw + sg
        up &= ok
        dn &= c >= vw - sg
    if row == 114:
        extra["target"] = "vwap2"
    if row == 115:
        extra["trail_fast"] = E1.ema(c, 5)
    if row in (116, 117, 118):
        up &= (c > vw + 0.5 * sg) & (fast > vw + 0.25 * sg)
        dn &= (c < vw - 0.5 * sg) & (fast < vw - 0.25 * sg)
    if row in (117, 118):
        width = np.where(c > 0, sg / c, np.nan)
        med = pd.Series(width).rolling(480, min_periods=480).median().to_numpy()
        ok = width >= med if row == 117 else width <= med
        up &= ok
        dn &= ok

    # cost-aware gates
    gates = {121: 0.0010, 122: 0.0015, 123: 0.0025, 124: 0.0050}
    if row in gates:
        ok = a >= gates[row] * c
        up &= ok
        dn &= ok
    if row == 125:
        pct = pd.Series(a).rolling(100, min_periods=100).quantile(0.7).to_numpy()
        up &= a > pct
        dn &= a > pct
    if row == 126:
        bw = pd.Series(c).rolling(20, min_periods=20).std().to_numpy()
        med = pd.Series(bw).rolling(100, min_periods=100).median().to_numpy()
        ok = (bw > med) & (bw > np.concatenate([[bw[0]], bw[:-1]]))
        up &= ok
        dn &= ok
    if row == 127:
        vz = (v - pd.Series(v).rolling(100, min_periods=100).mean().to_numpy()) / \
             np.maximum(pd.Series(v).rolling(100, min_periods=100).std().to_numpy(), 1e-12)
        ok = (vz > 1.5) & (a > pd.Series(a).rolling(100, min_periods=100).median().to_numpy())
        up &= ok
        dn &= ok
    if row == 128:
        r = pd.Series(c).pct_change()
        rv = np.sqrt((r ** 2).rolling(12, min_periods=12).mean().to_numpy() /
                     (r ** 2).rolling(96, min_periods=96).mean().to_numpy())
        up &= rv > 1.2
        dn &= rv > 1.2

    # inversions and fades
    if row in (129, 130, 132, 134):
        up, dn = dn, up
        extra["stop"] = 1.5
        extra["time_stop"] = {129: 20, 130: 24, 132: 16, 134: 24}[row]
        if row == 130:
            extra["target"] = "vwap"
    if row == 131:
        up = armed & (c < vw - 1.5 * sg)
        dn = armed & (c > vw + 1.5 * sg)
        extra["stop"] = 1.5
        extra["target"] = "vwap"
    if row == 133:
        prev_c = np.concatenate([[c[0]], c[:-1]])
        up = cross_up & (prev_c < np.concatenate([[fast[0]], fast[:-1]]))
        dn = np.zeros(n, bool)
        extra["target"] = "vwap"
        extra["stop"] = "confirm_high"

    # higher-timeframe alignment: same-chart proxies from the served bars
    if 135 <= row <= 140:
        e50 = E1.ema(c, 50)
        if row == 135:
            ok = c > np.concatenate([[vw[0]], vw[:-1]])
            up &= ok
            dn &= ok
        if row == 136:
            ok = fast > vw
            up &= ok
            dn &= ok
        if row == 137:
            up &= (fast > vw)
            dn &= (fast < vw)
        if row == 138:
            up &= ~(c < e50)
            dn &= ~(c < e50)
        if row == 139:
            up &= fast > vw
            dn &= fast < vw
        if row == 140:
            rv = E1.rolling_vwap(pd.DataFrame(dict(high=h, low=l, close=c,
                                                   volume=v)), 30)
            up &= c > rv
            dn &= c < rv

    # management
    if row in (141, 150):
        extra["stop"] = 1.5
    if row == 141:
        extra["breakeven"] = 1.0
    if row == 142:
        extra["time_stop"] = 30
    if row == 143:
        extra["cooldown"] = 12
    if row == 144:
        extra["daily_stop"] = 3
    if row == 145:
        extra["pyramid"] = True
    if row == 146:
        extra["one_leg"] = 1
    if row == 147:
        extra["one_leg"] = -1
    if row == 150:
        extra["risk_frac"] = 0.0025

    return dict(o=o, h=h, l=l, c=c, v=v, ts=df["open_ts"].to_numpy(np.int64),
                up=up, dn=dn, xl=xl, xs=xs, fast=fast, ref=vw, atr=a,
                sigma=sg, tf=tf, extra=extra,
                dt=dt)


# ── simulator ──────────────────────────────────────────────────────────────
def simulate(sig, fees, use_funding=False, funding_events=None):
    o, h, l, c, ts = sig["o"], sig["h"], sig["l"], sig["c"], sig["ts"]
    up, dn, xl, xs = sig["up"], sig["dn"], sig["xl"], sig["xs"]
    ex = sig["extra"]
    n = len(o)
    cash = INIT
    pos = 0
    qty = 0.0
    entry = 0.0
    entry_i = 0
    entry_fee = 0.0
    trades = []
    funded = 0.0
    fund_trade = 0.0
    pend = 0
    pend_limit = None
    pend_expire = 0
    last_exit = -10_000
    loss_streak = 0
    stop_day = None
    eq = np.empty(n)
    eq[0] = INIT
    frate = {}
    if use_funding and funding_events:
        for t, r in funding_events:
            i = int(np.searchsorted(ts, t, side="right") - 1)
            if 0 <= i < n:
                frate[i] = frate.get(i, 0.0) + r
    fee, slip = fees["fee"] / 1e4, fees["slip"] / 1e4
    stop_price = None
    stop_level = None
    stack = 1.0
    for i in range(1, n):
        # pending orders fill at/open within this bar
        if pend_limit is not None and pos == 0:
            lim, side, exp = pend_limit
            touched = (l[i] <= lim) if side > 0 else (h[i] >= lim)
            if touched:
                fill = lim
                qty = cash / fill
                entry_fee = abs(qty * fill) * fee
                cash -= qty * fill + entry_fee
                entry, entry_i, pos = fill, i, side
                pend_limit = None
            elif i >= exp:
                ex["missed"] += 1
                pend_limit = None
        elif pend != 0 and pos == 0:
            fill = o[i] * (1 + slip * (1 if pend > 0 else -1))
            qty = cash / fill
            entry_fee = abs(qty * fill) * fee
            cash -= qty * fill + entry_fee
            entry, entry_i, pos, stack = fill, i, pend, 1.0
            if isinstance(ex.get("stop"), float):
                stop_level = ex["stop"] * sig["atr"][i]
                stop_price = entry - stop_level if pos > 0 else entry + stop_level
            pend = 0
        if pos != 0 and i in frate:
            pay = qty * c[i] * frate[i]
            cash -= pay
            funded += pay
            fund_trade += pay
        # risk exits BEFORE signal exit (stop-first)
        closed = False
        if pos != 0:
            hit = (stop_price is not None and
                   ((l[i] <= stop_price) if pos > 0 else (h[i] >= stop_price)))
            if hit:
                fill = min(o[i], stop_price) if pos > 0 else max(o[i], stop_price)
                closed = True
                reason = "stop"
            elif ex.get("time_stop") and i - entry_i >= ex["time_stop"]:
                fill = o[i]
                closed = True
                reason = "time"
            elif ex.get("target") == "vwap2":
                lvl = sig["ref"][i] + 2 * sig["sigma"][i] if pos > 0 else \
                      sig["ref"][i] - 2 * sig["sigma"][i]
                hit2 = (h[i] >= lvl) if pos > 0 else (l[i] <= lvl)
                if hit2:
                    fill = lvl
                    closed = True
                    reason = "target"
            elif ex.get("target") == "vwap":
                lvl = sig["ref"][i]
                hit2 = (h[i] >= lvl) if pos > 0 else (l[i] <= lvl)
                if hit2:
                    fill = lvl
                    closed = True
                    reason = "target"
            elif pos > 0 and xl[i] or pos < 0 and xs[i]:
                fill = o[i]
                closed = True
                reason = "ema"
            if closed:
                fill *= (1 - slip * (1 if pos > 0 else -1))
                f = abs(qty * stack * fill) * fee
                pnl = qty * stack * (fill - entry) - entry_fee - f - fund_trade
                cash += qty * stack * fill - f
                trades.append(dict(pnl=pnl, side=pos, entry_i=entry_i,
                                   exit_i=i, ret=pnl / INIT * 100.0,
                                   reason=reason))
                loss_streak = loss_streak + 1 if pnl <= 0 else 0
                last_exit = i
                pos, qty, qty, stack = 0, 0.0, 0.0, 1.0
                stop_price = stop_level = None
                fund_trade = 0.0
        if pos == 0:
            one = ex.get("one_leg")
            can_up = up[i] and one != -1
            can_dn = dn[i] and one != 1
            cool = ex.get("cooldown", 0)
            if cool and i - last_exit < cool:
                can_up = can_dn = False
            if stop_day is not None and sig["dt"][i].date() == stop_day:
                can_up = can_dn = False
            if can_up or can_dn:
                side = 1 if can_up else -1
                if ex.get("limit") == "ema":
                    pend_limit = (sig["fast"][i], side, i + ex["limit_bars"])
                else:
                    pend = side
        eq[i] = cash + qty * c[i]
    if pos != 0:
        f = abs(qty * stack * o[-1]) * fee
        pnl = qty * stack * (o[-1] - entry) - entry_fee - f - fund_trade
        cash += qty * stack * o[-1] - f
        trades.append(dict(pnl=pnl, side=pos, entry_i=entry_i,
                           exit_i=n - 1, ret=pnl / INIT * 100.0, reason="eod"))
        eq[-1] = cash
    resid = eq[-1] - INIT - sum(t["pnl"] for t in trades)
    tol = max(1e-6, 1e-8 * abs(float(eq[-1])))
    if abs(resid) > tol:
        raise AssertionError(f"identity failed: {resid}")
    return dict(eq=eq, trades=trades, funded=funded, resid=resid,
                missed=ex.get("missed", 0))


def metrics(res, bh):
    out = E1._metrics(res, bh)
    out["n_missed"] = int(res.get("missed", 0))
    out["pnl_identity_resid"] = round(float(res["resid"]), 10)
    out["fees_paid"] = round(float(sum(t["pnl"] for t in res["trades"])), 4)
    return out


def run_one(paths, params):
    row = int(params["id"])
    if row not in ROWS2:
        raise RuntimeError(f"row {row} is not part of Suite 2")
    tf = str(params["tf"])
    if tf != ROWS2[row]:
        raise RuntimeError(f"row {row}: declared tf {ROWS2[row]}, got {tf}")
    costs = str(params.get("costs", "repo")).lower()
    if costs not in ("repo", "zero"):
        raise ValueError(f"unknown costs {costs!r}")
    use_funding = bool(params.get("funding", True))
    fees = LIMIT if row == 104 else (E1.ZERO if costs == "zero" else REPO)
    if row in XROWS:
        raise RuntimeError(f"row {row}: NO DATA — cross-sectional selector "
                           "book not faithfully implemented (pre-registration addendum)")
    df = _load(paths[0])
    if row in RESAMPLED:
        if tf != "3m":
            raise RuntimeError(f"row {row}: 3m resample declared")
        df = resample_3m(df)
    fund_path = paths[1] if len(paths) > 1 and str(paths[1]).endswith(".json") else None
    fevents = E1._load_funding(fund_path) if (use_funding and fund_path) else []
    sig = build(df, row)
    res = simulate(sig, fees, bool(use_funding and fund_path), fevents)
    bh = float(df["close"].iloc[-1] / df["close"].iloc[0] - 1.0) * 100.0
    m = metrics(res, bh)
    # control: unmodified base on the same slice
    csig = build(df, 0)  # unmodified EMA11 x daily VWAP skeleton
    ctl = simulate(csig, fees, bool(use_funding and fund_path), fevents)
    cm = E1._metrics(ctl, bh)
    m.update(dict(row=row, costs=costs, fee_bps_per_side=fees["fee"],
                  slippage_bps_per_side=fees["slip"],
                  cost_bp_roundtrip=2 * (fees["fee"] + fees["slip"]),
                  funding_charged=bool(use_funding and fund_path),
                  resampled_3m=row in RESAMPLED, bars=int(len(df)),
                  control_net_pct=cm["net_pct"], control_pf=cm["profit_factor"],
                  zero_cost_ret_pct=round(float((simulate(sig, E1.ZERO, False, [])["eq"][-1] /
                                                 INIT - 1) * 100), 4)))
    split_i = int(0.7 * len(df))
    tr = [t for t in res["trades"] if t["entry_i"] >= split_i]
    pos = np.array([t["pnl"] for t in tr if t["pnl"] > 0])
    neg = np.array([-t["pnl"] for t in tr if t["pnl"] < 0])
    m["test_n"] = len(tr)
    m["test_net_pct"] = round(float(sum(t["pnl"] for t in tr) / INIT * 100), 4)
    m["test_pf"] = round(float(pos.sum() / neg.sum()), 6) if neg.sum() > 0 else None
    pn = np.array([t["pnl"] for t in res["trades"]])
    ps = np.sort(pn[pn > 0])[::-1][:5]
    m["conc_top5_share_pct"] = round(float(ps.sum() / pn[pn > 0].sum() * 100), 4) \
        if pn[pn > 0].sum() > 0 else None
    rng = np.random.default_rng(7)
    lb = None
    if len(pn) >= 30:
        blk = max(1, int(round(len(pn) ** (1 / 3))))
        dr = []
        for _ in range(500):
            st = rng.integers(0, len(pn) - blk + 1, size=max(1, len(pn) // blk))
            dr.append(float(np.concatenate([pn[s:s + blk] for s in st])[:len(pn)].mean()))
        lb = round(float(np.percentile(dr, 2.5)), 6)
    m["boot_exp_lb"] = lb
    gates = dict(net=m["net_pct"] > 0, pf=m["profit_factor"] is not None and
                 m["profit_factor"] > 1.2, n=m["n_trades"] >= 30,
                 oos=m["test_net_pct"] > 0, boot=lb is not None and lb > 0,
                 conc=m["conc_top5_share_pct"] is not None and
                 m["conc_top5_share_pct"] < 100,
                 control=m["net_pct"] > m["control_net_pct"])
    m["gates"] = gates
    m["gate_pass"] = all(gates.values())
    m["dsr_proxy"] = round(float(
        (np.diff(res["eq"]) / np.maximum(res["eq"][:-1], 1e-12)).mean() /
        max(float((np.diff(res["eq"]) / np.maximum(res["eq"][:-1], 1e-12)).std()), 1e-12) *
        np.sqrt(len(res["eq"])) - np.sqrt(2 * np.log(100))), 6)
    prov = dict(adapter="emavwapv2", engine_version="emavwapv2-1", row=row,
                definition="Downloads/EMA×VWAP Suite 2 (#101–150)-claude.md")
    tables = [dict(kind="trade", **t) for t in res["trades"][:200]]
    return m, prov, tables


if __name__ == "__main__":
    print("emavwapv2: run via vrun.py / code/_emavwapv2_audit.py")
