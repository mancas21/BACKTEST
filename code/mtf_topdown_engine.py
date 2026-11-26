#!/usr/bin/env python
"""Harness runner for the attached MTF top-down strategy.

The SIGNAL is imported by IDENTITY from `code/mtf_topdown_source.py`, a
byte-identical copy of the attachment (sha bound into every run_id). This file
adds only the repo execution regime: 11 bps RT + real funding at settlements,
with author-cost and zero-cost controls measured on the same signals.
See results/mtf_topdown_pre_registration.md.

Audit: code/_mtf_topdown_audit.py (parity with the source's own engine first).
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

import mtf_topdown_source as S

INIT = 10_000.0
REPO_FEE, REPO_SLIP = 0.0005, 0.00005   # 5.0 + 0.5 bps per side
AUTHOR_FEE, AUTHOR_SLIP = 0.0004, 0.0001
ZERO_FEE, ZERO_SLIP = 0.0, 0.0


def load_funding(path):
    if not path or not os.path.exists(path):
        return {}
    recs = json.load(open(path, encoding="utf-8"))
    return {int(r["t"]): float(r["r"]) for r in recs}


def execute(f, cfg, fee, slip, funding_rates=None):
    """The source's backtest rules, verbatim, plus harness costs and funding."""
    o, h, l, c = (f[k].to_numpy() for k in ("open", "high", "low", "close"))
    d4, st1 = f["dir4"].to_numpy(), f["st1"].to_numpy()
    evt_l, evt_s = f["evt_l"].to_numpy(), f["evt_s"].to_numpy()
    swl, swh, atr15 = f["sw_low"].to_numpy(), f["sw_high"].to_numpy(), f["atr15"].to_numpy()
    sh5, sh5i, sl5, sl5i = (f[k].to_numpy() for k in ("sh5", "sh5i", "sl5", "sl5i"))
    # pandas 3 may carry a µs DatetimeIndex; normalize to ns before ms math
    ts = (f.index.as_unit("ns").to_numpy(np.int64) // 1_000_000).astype(np.int64)
    n, ttl = len(f), cfg.setup_ttl_15m * 3
    settle = {}
    for t, r in (funding_rates or {}).items():
        i = int(np.searchsorted(ts, t, side="right") - 1)
        if 0 <= i < n:
            settle[i] = settle.get(i, 0.0) + r

    eq = cfg.init_equity
    pos, armed, trades = None, None, []
    fund_trade = funded = 0.0
    for i in range(n):
        if pos is not None:
            s, px, why = pos["side"], None, None
            if s == 1:
                if l[i] <= pos["sl"]:
                    px, why = min(o[i], pos["sl"]) * (1 - slip), "sl"
                elif h[i] >= pos["tp"]:
                    px, why = pos["tp"], "tp"
            else:
                if h[i] >= pos["sl"]:
                    px, why = max(o[i], pos["sl"]) * (1 + slip), "sl"
                elif l[i] <= pos["tp"]:
                    px, why = pos["tp"], "tp"
            if px is None and i - pos["i0"] + 1 >= cfg.max_hold_5m:
                px, why = c[i], "time"
            if px is None and i == n - 1:
                px, why = c[i], "eod"
            if px is not None:
                gross = s * (px - pos["entry"]) * pos["qty"]
                fees = fee * pos["qty"] * (pos["entry"] + px)
                pnl = gross - fees - fund_trade
                eq += pnl
                trades.append(dict(entry_time=f.index[pos["i0"]], exit_time=f.index[i],
                                   side=s, entry=float(pos["entry"]), exit=float(px),
                                   sl=float(pos["sl"]), tp=float(pos["tp"]),
                                   qty=float(pos["qty"]), pnl=float(pnl),
                                   r=float(pnl / pos["risk_usd"]),
                                   bars=int(i - pos["i0"] + 1), reason=why,
                                   equity=float(eq), funding=float(fund_trade)))
                pos, armed, fund_trade = None, None, 0.0
            if i in settle and pos is not None:
                pay = pos["qty"] * c[i] * settle[i]
                funded += pay
                fund_trade += pay
            continue
        if i in settle and pos is not None:
            pay = pos["qty"] * c[i] * settle[i]
            funded += pay
            fund_trade += pay
        if evt_l[i] and cfg.allow_long:
            armed = (1, i, swl[i])
        elif evt_s[i] and cfg.allow_short:
            armed = (-1, i, swh[i])
        if armed is not None:
            side, ai, ext = armed
            if (i - ai > ttl or d4[i] != side or st1[i] != side or
                    (side == 1 and c[i] < ext) or (side == -1 and c[i] > ext)):
                armed = None
        if armed is None or i + 1 >= n:
            continue
        side, ai, ext = armed
        lo_i = max(0, ai - 2)
        if side == 1:
            trig = sh5i[i] >= ai - 2 and c[i] > sh5[i]
            stop_ref = min(ext, l[lo_i:i + 1].min())
        else:
            trig = sl5i[i] >= ai - 2 and c[i] < sl5[i]
            stop_ref = max(ext, h[lo_i:i + 1].max())
        if not trig:
            continue
        entry = o[i + 1] * (1 + slip * side)
        sl = stop_ref - side * cfg.sl_atr_buf * atr15[i]
        risk = side * (entry - sl)
        armed = None
        if not (cfg.min_risk_pct * entry <= risk <= cfg.max_risk_pct * entry) or eq <= 0:
            continue
        qty = min(eq * cfg.risk_pct / risk, eq * max(cfg.max_leverage * entry, 1e-12))
        pos = dict(side=side, i0=i + 1, entry=entry, sl=sl,
                   tp=entry + side * cfg.rr * risk,
                   qty=qty, risk_usd=qty * risk)
    if pos is not None:
        px = c[-1]
        gross = pos["side"] * (px - pos["entry"]) * pos["qty"]
        fees = fee * pos["qty"] * (pos["entry"] + px)
        pnl = gross - fees - fund_trade
        eq += pnl
        trades.append(dict(entry_time=f.index[pos["i0"]], exit_time=f.index[-1],
                           side=pos["side"], entry=float(pos["entry"]), exit=float(px),
                           sl=float(pos["sl"]), tp=float(pos["tp"]),
                           qty=float(pos["qty"]), pnl=float(pnl),
                           r=float(pnl / pos["risk_usd"]),
                           bars=int(n - pos["i0"]), reason="eod", equity=float(eq),
                           funding=float(fund_trade)))
    resid = eq - cfg.init_equity - sum(t["pnl"] for t in trades)
    if abs(resid) > max(1e-6, 1e-8 * abs(eq)):
        raise AssertionError(f"accounting identity failed: {resid}")
    return pd.DataFrame(trades), float(funded), float(resid)


def summarize(tr, funded, init):
    if tr.empty:
        return dict(n_trades=0, net_pct=0.0, profit_factor=None,
                    max_dd_pct=0.0, win_pct=None, funding_paid=0.0)
    eq = init + tr["pnl"].cumsum().to_numpy()
    peak = np.maximum.accumulate(np.r_[init, eq])[1:]
    gp = float(tr.loc[tr.pnl > 0, "pnl"].sum())
    gl = float(-tr.loc[tr.pnl < 0, "pnl"].sum())
    return dict(n_trades=int(len(tr)),
                net_pct=round(float((eq[-1] / init - 1) * 100), 4),
                profit_factor=round(gp / gl, 6) if gl > 0 else None,
                max_dd_pct=round(float((eq / peak - 1).min() * 100), 4),
                win_pct=round(float((tr.pnl > 0).mean() * 100), 3),
                funding_paid=round(funded, 4))


def run_one(paths, params):
    tf = str(params["tf"])
    if tf != "5m":
        raise RuntimeError(f"MTF top-down declares a 5m base, got {tf!r}")
    costs = str(params.get("costs", "repo")).lower()
    if costs not in ("repo", "author", "zero"):
        raise ValueError(f"unknown costs {costs!r}")
    use_funding = bool(params.get("funding", True))
    cfg = S.Cfg()
    df5 = S.load_csv(paths[0])
    f = S.build_features(df5, cfg)
    fund_path = paths[1] if len(paths) > 1 and str(paths[1]).endswith(".json") else None
    rates = load_funding(fund_path) if use_funding else {}
    fee, slip = {"repo": (REPO_FEE, REPO_SLIP), "author": (AUTHOR_FEE, AUTHOR_SLIP),
                 "zero": (ZERO_FEE, ZERO_SLIP)}[costs]
    tr, funded, resid = execute(f, cfg, fee, slip, rates)
    m = summarize(tr, funded, cfg.init_equity)
    bh = float(df5["close"].iloc[-1] / df5["close"].iloc[0] - 1.0) * 100.0
    m.update(dict(strategy="mtftopdown", symbol="SOLUSDT", timeframe="5m",
                  costs=costs, fee_bps_per_side=fee * 1e4,
                  slippage_bps_per_side=slip * 1e4,
                  cost_bp_roundtrip=2 * (fee + slip) * 1e4,
                  funding_charged=bool(use_funding and fund_path),
                  bh_return_pct=round(bh, 4),
                  pnl_identity_resid=round(resid, 10),
                  bars=int(len(df5)),
                  window_start_utc=str(df5.index[0]), window_end_utc=str(df5.index[-1])))
    for key, (ff, ss) in (("author", (AUTHOR_FEE, AUTHOR_SLIP)),
                          ("zero", (ZERO_FEE, ZERO_SLIP))):
        t2, _, _ = execute(f, cfg, ff, ss, {})
        m[f"net_{key}_pct"] = summarize(t2, 0.0, cfg.init_equity)["net_pct"]
    split = int(len(df5) * 0.7)
    cut = df5.index[split]
    te = tr[tr["entry_time"] >= cut] if len(tr) else tr
    pos = te.loc[te.pnl > 0, "pnl"].to_numpy(float)
    neg = -te.loc[te.pnl < 0, "pnl"].to_numpy(float)
    m["test_n"] = int(len(te))
    m["test_net_pct"] = round(float(te.pnl.sum() / cfg.init_equity * 100), 4)
    m["test_pf"] = round(float(pos.sum() / neg.sum()), 6) if neg.size and neg.sum() > 0 else None
    pn = tr.pnl.to_numpy(float) if len(tr) else np.array([])
    top5 = np.sort(pn[pn > 0])[::-1][:5]
    m["conc_top5_share_pct"] = (round(float(top5.sum() / pn[pn > 0].sum() * 100), 4)
                                if pn[pn > 0].sum() > 0 else None)
    lb = None
    if len(pn) >= 30:
        rng = np.random.default_rng(7)
        blk = max(1, int(round(len(pn) ** (1 / 3))))
        draws = []
        for _ in range(500):
            st = rng.integers(0, len(pn) - blk + 1, size=max(1, len(pn) // blk))
            draws.append(float(np.concatenate([pn[s:s + blk] for s in st])[:len(pn)].mean()))
        lb = round(float(np.percentile(draws, 2.5)), 6)
    m["boot_exp_lb"] = lb
    gates = dict(n=m["n_trades"] >= 100,
                 pf=m["profit_factor"] is not None and m["profit_factor"] > 1.2,
                 net=m["net_pct"] > 0,
                 oos=m["test_net_pct"] > 0,
                 boot=lb is not None and lb > 0,
                 conc=m["conc_top5_share_pct"] is not None and
                 m["conc_top5_share_pct"] < 100,
                 bh=m["net_pct"] > bh)
    m["gates"] = gates
    m["gate_pass"] = all(gates.values()) and m["n_trades"] >= 100
    prov = dict(adapter="mtftopdown", engine_version="mtftopdown-1",
                source_sha256="833aedf770bad9c3f7b0b7860d5cbe9d2a2a2c790319b1b175a4f62f16a2d945",
                source_file="mtf_topdown_source.py")
    tables = []
    for _, r in tr.iterrows():
        tables.append({k: (str(v) if k.endswith("_time") else v)
                       for k, v in r.to_dict().items()})
    return m, prov, tables[:500]


if __name__ == "__main__":
    print("mtftopdown: run via vrun.py / code/_mtf_topdown_audit.py")
