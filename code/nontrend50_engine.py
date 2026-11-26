#!/usr/bin/env python
"""Non-Trend 50-Strategy Suite (#51–100) — harness runner.

Source: `Downloads/Non-Trend 50-Strategy Suite (#51–100)-claude.md`
(natural-language spec, no code). Cross-sectional, dollar-neutral books;
ranks at bar close, fills at next open, real funding at settlements, repo
11 bps RT on turnover. Every row is measured against the in-artifact #51
control. See results/nontrend50_pre_registration.md for the frozen grid.

One artifact = one numbered row on a pseudo-symbol (U_1H / T_5M / F_1H)
whose inputs are ALL the CSVs of that universe. The accounting identity
eq[-1] - INIT == sum(period pnl) is asserted inside every artifact.

Audit: code/_nontrend50_audit.py (before any market number).
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
INIT = 10000.0
FEE = 5.0    # bps per side
SLIP = 0.5   # bps per side
BARS_YEAR = 24 * 365

T_SYMBOLS = ["BTCUSDT", "ETHUSDT", "HYPEUSDT", "JUPUSDT",
             "SOLUSDT", "SUIUSDT", "XRPUSDT"]
F_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT",
             "SUIUSDT", "ARBUSDT", "JUPUSDT", "HYPEUSDT"]
EXCLUDE = {"NVDAUSDT", "SOLUSDC", "SPCXUSDT", "SPXUSDT"}


def u_symbols():
    syms = sorted({os.path.basename(p).split("_")[0] for p in
                   glob.glob(os.path.join(DATA, "binance_klines_1h", "*_1h.csv"))
                   if "_tail_" not in os.path.basename(p)})
    return [s for s in syms if s not in EXCLUDE]


# ── panel ──────────────────────────────────────────────────────────────────
def load_panel(symbols, tf, taker=False):
    base = os.path.join(DATA, "binance_klines_5m_taker" if taker
                        else "binance_klines_1h")
    frames = {}
    for s in symbols:
        p = os.path.join(base, f"{s}_{tf}.csv")
        if not os.path.exists(p):
            raise FileNotFoundError(p)
        df = pd.read_csv(p)
        d = df.set_index(df["open_ts"].to_numpy(np.int64))
        frames[s] = d
    common = None
    for d in frames.values():
        common = d.index if common is None else common.intersection(d.index)
    common = np.sort(common)
    if len(common) < 500:
        raise RuntimeError("panel has fewer than 500 common bars")
    O = np.column_stack([frames[s].loc[common, "open"].to_numpy(float) for s in symbols])
    C = np.column_stack([frames[s].loc[common, "close"].to_numpy(float) for s in symbols])
    V = np.column_stack([frames[s].loc[common, "volume"].to_numpy(float) for s in symbols])
    TB = None
    if taker:
        TB = np.column_stack([frames[s].loc[common, "taker_buy_base"].to_numpy(float)
                              for s in symbols])
    return dict(ts=common, symbols=symbols, O=O, C=C, V=V, TB=TB)


def load_funding_map(symbols, ts):
    out = {}
    for s in symbols:
        p = os.path.join(DATA, "binance_funding", f"{s}_funding.json")
        if not os.path.exists(p):
            out[s] = []
            continue
        recs = json.load(open(p, encoding="utf-8"))
        ev = []
        for r in recs:
            t = int(r["t"])
            i = int(np.searchsorted(ts, t, side="right") - 1)
            if 0 <= i < len(ts):
                ev.append((i, float(r["r"])))
        out[s] = ev
    return out


# ── primitives ─────────────────────────────────────────────────────────────
def roc(C, n):
    out = np.full_like(C, np.nan, dtype=float)
    out[n:] = C[n:] / C[:-n] - 1.0
    return out


def ret(C):
    r = np.full_like(C, np.nan, dtype=float)
    r[1:] = C[1:] / C[:-1] - 1.0
    return r


def roll_vol(r, n):
    out = np.full_like(r, np.nan, dtype=float)
    for j in range(r.shape[1]):
        out[:, j] = pd.Series(r[:, j]).rolling(n, min_periods=n).std().to_numpy()
    return out * np.sqrt(BARS_YEAR)


def rolling_beta(r, market, n):
    out = np.full_like(r, np.nan, dtype=float)
    m = pd.Series(market)
    for j in range(r.shape[1]):
        x = pd.Series(r[:, j])
        cov = x.rolling(n, min_periods=n).cov(m)
        var = m.rolling(n, min_periods=n).var()
        out[:, j] = (cov / var).to_numpy()
    return out


def zscore(X):
    mu = np.nanmean(X, axis=1, keepdims=True)
    sd = np.nanstd(X, axis=1, keepdims=True)
    return (X - mu) / np.maximum(sd, 1e-12)


def rank_pct(X):
    """Cross-sectional percentile rank, higher = stronger. NaNs get 0.5."""
    out = np.full_like(X, 0.5, dtype=float)
    for i in range(X.shape[0]):
        row = X[i]
        ok = np.isfinite(row)
        if ok.sum() >= 2:
            order = np.argsort(np.argsort(row[ok]))
            out[i, ok] = (order + 1.0) / (ok.sum() + 1.0)
    return out


def skew_rows(R, n):
    out = np.full_like(R, np.nan, dtype=float)
    for j in range(R.shape[1]):
        s = pd.Series(R[:, j])
        m = s.rolling(n, min_periods=n).mean()
        sd = s.rolling(n, min_periods=n).std()
        third = s.rolling(n, min_periods=n).apply(
            lambda x: np.mean((x - np.mean(x)) ** 3), raw=True)
        out[:, j] = (third / np.maximum(sd ** 3, 1e-12)).to_numpy()
    return out


# ── row scores ─────────────────────────────────────────────────────────────
def base_score(p, gate=True):
    s = roc(p["C"], 168)
    if gate:
        g = roc(p["C"], 336)
        s = np.where(np.isfinite(s) & np.isfinite(g) & (g > 0), s, -np.inf)
    return s


def score_for_row(row, p, fund_rates=None, sleeve_ok=None):
    C, V, TB = p["C"], p["V"], p["TB"]
    r = ret(C)
    btc_idx = p["symbols"].index("BTCUSDT") if "BTCUSDT" in p["symbols"] else 0
    if row == 51:
        return base_score(p), 336, None
    if row == 52:
        return base_score(p), 336, dict(k=3)
    if row == 53:
        s = C / np.concatenate([np.full((24, C.shape[1]), np.nan), C[:-24]], 0) - 1.0
        return s, 336, None
    if row == 54:
        s = roc(C, 168) / np.maximum(roll_vol(r, 168), 1e-12)
        return s, 336, None
    if row == 55:
        beta = rolling_beta(r, r[:, btc_idx], 336)
        resid = np.nancumsum(r - beta * r[:, btc_idx:btc_idx + 1], axis=0)
        s = resid - np.concatenate([np.full((168, C.shape[1]), np.nan), resid[:-168]], 0)
        return s, 336, dict(beta=beta)
    if row == 56:
        a, b, c = rank_pct(roc(C, 72)), rank_pct(roc(C, 168)), rank_pct(roc(C, 336))
        return (a + b + c) / 3.0, 168, None
    if row == 57:
        return base_score(p), 336, dict(weight=1.0 / np.maximum(roll_vol(r, 168), 1e-12))
    if row == 58:
        return base_score(p), 84, dict(sleeves=4)
    if row == 59:
        return base_score(p), 168, dict(hold_band=4)
    if row == 60:
        g = roc(C, 336)
        s = np.where((g > 0) | (g < 0), base_score(p, gate=False), -np.inf)
        return s, 336, None
    if 61 <= row <= 68:
        s, rb, extra = base_score(p), 336, {}
        if row == 61:
            extra["vol_target"] = 0.25
        elif row == 62:
            extra["dd_brake"] = (0.15, 0.075)
        elif row == 63:
            extra["btc_vol_gate"] = True
        elif row == 64:
            extra["dispersion_gate"] = True
        elif row == 65:
            extra["beta_neutral"] = True
        elif row == 66:
            extra["leg_stop"] = -0.12
        elif row == 67:
            extra["crash_skip"] = 0.10
        elif row == 68:
            extra["exclude_illiquid"] = 3
        return s, rb, extra
    if 69 <= row <= 76:
        imb = TB / np.maximum(V, 1e-12)  # fraction of volume bought by taker
        agg = lambda n: pd.DataFrame(imb).rolling(n, min_periods=n).mean().to_numpy()
        if row == 69:
            return agg(288), 288, None          # 24h of 5m bars
        if row == 70:
            return agg(2016) - agg(8640), 576, None
        if row == 71:
            rz = zscore(agg(288))
            rp = zscore(pd.DataFrame(r).rolling(288, min_periods=288).mean().to_numpy())
            return rz - rp, 288, None
        if row == 72:
            vol24 = pd.DataFrame(V).rolling(288, min_periods=288).sum().to_numpy()
            vol30 = pd.DataFrame(V).rolling(8640, min_periods=8640).mean().to_numpy() * 288
            shock = vol24 > 2.0 * vol30
            s = np.where(shock, -roc(C, 288), -np.inf)
            return s, 288, dict(one_side_only=True)
        if row == 73:
            daily = pd.DataFrame(imb).rolling(288, min_periods=288).mean().to_numpy()[::288]
            cnt = pd.DataFrame(daily).rolling(7, min_periods=7).apply(
                lambda x: (x > 0.5).sum(), raw=True).to_numpy()
            s = np.full_like(C, np.nan)
            k = min(len(cnt), C.shape[0] // 288)
            s[:k * 288] = np.repeat(cnt[:k], 288, axis=0)
            return s, 864, dict(threshold=(6, 1))
        if row == 74:
            net = pd.DataFrame((2.0 * TB - V)).rolling(2016, min_periods=2016).sum().to_numpy()
            den = pd.DataFrame(V).rolling(8640, min_periods=8640).mean().to_numpy() * 288
            return net / np.maximum(den, 1e-12), 864, None
        if row == 75:
            s = base_score(p)
            fl = pd.DataFrame(imb).rolling(2016, min_periods=2016).mean().to_numpy()
            return s, 336, dict(flow_filter=fl)
        if row == 76:
            s = agg(288)
            return s, 288, dict(funding_rank=True)
    if 77 <= row <= 82:
        fr = fund_rates or {}
        # funding rate carried forward onto bars, per symbol
        ev = np.zeros_like(C)
        for j, s in enumerate(p["symbols"]):
            for i, rate in fr.get(s, []):
                if i < len(ev):
                    ev[i, j] = rate
        frate = pd.DataFrame(ev).ffill().fillna(0.0).to_numpy()
        roll = lambda n: pd.DataFrame(frate).rolling(n, min_periods=n).mean().to_numpy()
        if row == 77:
            return -roll(504), 432, None       # 7d mean funding, short crowded
        if row == 78:
            return -(roll(216) - np.concatenate([np.full((216, C.shape[1]), np.nan),
                                                 roll(216)[:-216]], 0)), 432, None
        if row == 79:
            cum = pd.DataFrame(frate).rolling(168, min_periods=168).sum().to_numpy()
            return roc(C, 168) - cum, 336, None
        if row == 80:
            s = base_score(p)
            pct = pd.DataFrame(frate).rolling(2160, min_periods=2160).quantile(0.9).to_numpy()
            return s, 336, dict(funding_cap=pct)
        if row == 81:
            mu = pd.DataFrame(frate).rolling(2160, min_periods=2160).mean().to_numpy()
            sd = pd.DataFrame(frate).rolling(2160, min_periods=2160).std().to_numpy()
            z = (frate - mu) / np.maximum(sd, 1e-12)
            s = np.where(z > 2, -1.0, np.where(z < -2, 1.0, np.nan))
            return s, 24, dict(per_asset=True, hold=24)
        if row == 82:
            s7 = roll(504)
            prev = np.concatenate([np.full((504, C.shape[1]), np.nan), s7[:-504]], 0)
            s = np.where((prev > 0) & (s7 < 0), 1.0,
                         np.where((prev < 0) & (s7 > 0), -1.0, np.nan))
            return s, 24, dict(per_asset=True, hold=120, event=True)
    if 83 <= row <= 92:
        if row == 83:
            return -roll_vol(r, 336), 336, None
        if row == 84:
            day = pd.DataFrame(r).rolling(24, min_periods=24).max().to_numpy()
            s = -np.concatenate([np.full((720, C.shape[1]), np.nan), day[:-720]], 0)
            return s, 168, None
        if row == 85:
            beta = rolling_beta(r, r[:, btc_idx], 336)
            resid = r - beta * r[:, btc_idx:btc_idx + 1]
            return -roll_vol(resid, 336), 336, None
        if row == 86:
            return -skew_rows(r, 1440), 336, None
        if row == 87:
            beta = rolling_beta(r, r[:, btc_idx], 336)
            return -beta, 336, dict(beta=beta)
        if row == 88:
            hi = pd.DataFrame(C).rolling(720, min_periods=720).max().to_numpy()
            return C / np.maximum(hi, 1e-12), 336, None
        if row == 89:
            illiq = np.abs(r) / np.maximum(V * C, 1e-12)
            return pd.DataFrame(illiq).rolling(168, min_periods=168).mean().to_numpy(), 336, None
        if row == 90:
            dv = V * C
            a = pd.DataFrame(dv).rolling(168, min_periods=168).sum().to_numpy()
            b = pd.DataFrame(dv).rolling(720, min_periods=720).mean().to_numpy() * 168
            return a / np.maximum(b, 1e-12), 168, None
        if row == 91:
            corr = pd.DataFrame(r).rolling(336, min_periods=336).corr(
                pd.Series(r[:, btc_idx])).to_numpy()
            prev = np.concatenate([np.full((336, C.shape[1]), np.nan), corr[:-336]], 0)
            drop = prev - corr
            mask = drop >= np.nanpercentile(drop[np.isfinite(drop)], 50)
            return np.where(mask, base_score(p, gate=False), -np.inf), 336, None
        if row == 92:
            up = pd.DataFrame(r > 0).rolling(720, min_periods=720).sum().to_numpy()
            r30 = roc(C, 720)
            s = np.where(r30 > 0, up, np.where(r30 < 0, 720 - up, -np.inf))
            return s, 336, None
    if 93 <= row <= 100:
        raise RuntimeError(f"row {row}: composite — run only after its sleeves pass "
                           "the gates (results/nontrend50_pre_registration.md)")
    raise ValueError(f"unknown row {row}")


# ── simulator ──────────────────────────────────────────────────────────────
def simulate(p, score, rb, extra, fee_bps=FEE + SLIP, funding=True, frate=None):
    O, C, V = p["O"], p["C"], p["V"]
    T, S = C.shape
    units = np.zeros(S)
    cash = INIT
    eq = np.empty(T)
    eq[0] = INIT
    net_exposure = np.zeros(T)
    fund_matrix = np.zeros((T, S))
    for j, ev in (frate or {}).items():
        for bar, rate in ev:
            if 0 <= bar < T and 0 <= j < S:
                fund_matrix[bar, j] += rate
    pnl = []
    prev_eq = INIT
    rebalances = 0
    rebalance_bars = []
    net_at_fill = []
    last_rb = -rb
    k = extra.get("k", 2) if extra else 2
    hold_band = extra.get("hold_band") if extra else None
    w = (extra or {}).get("weight")
    brake_on = False
    upto = {}
    for i in range(1, T):
        if i - last_rb >= rb and i + 1 < T:
            sc = score[i]
            ok = np.isfinite(sc)
            target = np.zeros(S)
            can_trade = ok.sum() >= 2 * k
            if can_trade:
                idx = np.argsort(np.where(ok, sc, -np.inf))
                longs, shorts = idx[-k:], idx[:k]
                target[longs] = 0.5 / k
                target[shorts] = -0.5 / k
                if hold_band is not None:
                    # keep a held leg while its rank stays inside the wider
                    # top-/bottom-4 band; replace only legs that left it
                    band = hold_band
                    keep_l = idx[-band:]
                    keep_s = idx[:band]
                    desired_keep = np.zeros(S)
                    for j in np.where(units > 0)[0]:
                        if j in keep_l:
                            desired_keep[j] = units[j]
                    for j in np.where(units < 0)[0]:
                        if j in keep_s:
                            desired_keep[j] = units[j]
                    if np.any(desired_keep):
                        target = np.where(np.abs(desired_keep) > 0,
                                          desired_keep / np.abs(desired_keep).sum() *
                                          np.sum(np.abs(target)), target)
                if w is not None:
                    ww = np.where(ok, w[i], 1.0)
                    tw = np.abs(ww[longs]).sum() + np.abs(ww[shorts]).sum()
                    if tw > 0:
                        target[longs] = 0.5 * ww[longs] / tw
                        target[shorts] = -0.5 * ww[shorts] / tw
            # execute at next open, with the declared exposure overlays
            o = O[i + 1]
            scale = 1.0
            if extra and "vol_target" in extra and i >= 336:
                seg = eq[i - 335:i + 1] / eq[i - 336:i] - 1.0
                vol = float(np.std(seg)) * np.sqrt(BARS_YEAR)
                if vol > 0:
                    scale *= float(np.clip(extra["vol_target"] / vol, 0.25, 1.5))
            if extra and "dd_brake" in extra:
                peak = float(np.max(eq[:i]))
                hi, lo = extra["dd_brake"]
                if eq[i - 1] < (1.0 - hi) * peak:
                    brake_on = True
                elif eq[i - 1] > (1.0 - lo) * peak:
                    brake_on = False
                if brake_on:
                    scale *= 0.5
            if extra and "_scale" in extra:
                scale *= float(extra["_scale"][i])
            desired = target * eq[i - 1] / np.maximum(o, 1e-12) * scale
            delta = desired - units
            notional = np.abs(delta * o).sum()
            if can_trade:
                cash -= notional * fee_bps / 1e4
                units = desired
                net_at_fill.append(float(desired @ o))
                rebalances += 1
                rebalance_bars.append(i + 1)
                pnl.append(eq[i - 1] - prev_eq)
                prev_eq = eq[i - 1]
                last_rb = i
        if funding and frate:
            cash -= float(units @ (C[i] * fund_matrix[i]))
        eq[i] = cash + float(units @ C[i])
        net_exposure[i] = float(units @ C[i])
    if T > 1:
        pnl.append(eq[-1] - prev_eq)
    resid = eq[-1] - INIT - float(np.sum(pnl))
    if abs(resid) > 1e-6:
        raise AssertionError(f"accounting identity failed: {resid}")
    return dict(eq=eq, pnl=np.array(pnl), rebalances=rebalances, resid=resid,
                net_exposure=net_exposure,
                rebalance_bars=np.array(rebalance_bars, dtype=int),
                net_at_fill=np.array(net_at_fill))


def _stats(res, C, O):
    eq, pnl = res["eq"], res["pnl"]
    n = len(pnl)
    pos, neg = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    pf = float(pos / neg) if neg > 0 else (None if pos <= 0 else float("inf"))
    dd = eq / np.maximum.accumulate(eq) - 1.0
    months = pd.Series(eq, index=pd.to_datetime(
        np.arange(len(eq)) * 3600_000, utc=True)).resample("ME").last().pct_change().dropna()
    # five chronological folds
    edges = np.linspace(0, len(pnl), 6).astype(int)
    folds = [float(pnl[a:b].sum()) for a, b in zip(edges[:-1], edges[1:]) if b > a]
    rng = np.random.default_rng(7)
    lb = None
    if n >= 30:
        blk = max(1, int(round(n ** (1 / 3))))
        draws = []
        for _ in range(500):
            st = rng.integers(0, max(1, n - blk + 1), size=max(1, n // blk))
            draws.append(float(np.concatenate([pnl[s:s + blk] for s in st])[:n].mean()))
        lb = round(float(np.percentile(draws, 2.5)), 6)
    return dict(net_pct=round(float((eq[-1] / INIT - 1) * 100), 4),
                profit_factor=None if pf is None else round(pf, 6),
                n_trades=int(res["rebalances"]),
                max_dd_pct=round(float(dd.min()) * 100, 4),
                dd_p95_pct=round(float(np.percentile(dd, 5)) * 100, 4),
                months_green_pct=round(float((months > 0).mean()) * 100, 3)
                if len(months) else None,
                folds_profitable=sum(1 for f in folds if f > 0),
                folds_total=len(folds),
                boot_exp_lb=lb,
                pnl_identity_resid=round(float(res["resid"]), 10))


def run_one(paths, params):
    row = int(params["id"])
    tf = str(params["tf"])
    universe = "U" if (51 <= row <= 68 or 83 <= row <= 92) else \
               "T" if 69 <= row <= 76 else "F"
    want_tf = "5m" if universe == "T" else "1h"
    if tf != want_tf:
        raise RuntimeError(f"row {row}: declared tf {want_tf}, got {tf}")
    syms = u_symbols() if universe == "U" else T_SYMBOLS if universe == "T" else F_SYMBOLS
    csvs = [p for p in paths if str(p).endswith(".csv")]
    if len(csvs) != len(syms):
        raise RuntimeError(f"row {row}: expected {len(syms)} CSVs, got {len(csvs)}")
    p = load_panel(syms, want_tf, taker=(universe == "T"))
    fr_sym = load_funding_map(syms, p["ts"]) if universe in ("U", "F") else {}
    frate = {syms.index(s): ev for s, ev in fr_sym.items() if s in syms}
    if row in (65, 66, 68):
        raise RuntimeError(f"row {row}: NO DATA — overlay not faithfully "
                           "implemented (see pre-registration addendum)")
    score, rb, extra = score_for_row(row, p, fr_sym)
    extra = dict(extra or {})
    r = ret(p["C"])
    btc = 0 if "BTCUSDT" not in p["symbols"] else p["symbols"].index("BTCUSDT")
    if row == 63:
        v = pd.Series(r[:, btc]).rolling(168, min_periods=168).std().to_numpy() * np.sqrt(BARS_YEAR)
        pct = pd.Series(v).rolling(8760, min_periods=8760).quantile(0.8).to_numpy()
        extra["_scale"] = np.where(np.isfinite(v) & np.isfinite(pct) & (v > pct), 0.5, 1.0)
    elif row == 64:
        disp = np.nanstd(roc(p["C"], 168), axis=1)
        med = pd.Series(disp).rolling(2160, min_periods=2160).median().to_numpy()
        extra["_scale"] = np.where(np.isfinite(disp) & np.isfinite(med) &
                                   (disp < med), 0.0, 1.0)
    elif row == 67:
        spread = np.nanmean(score, axis=1)
        drop = spread - np.concatenate([np.full((168,), np.nan), spread[:-168]])
        extra["_scale"] = np.where(np.isfinite(drop) & (drop < -0.10), 0.0, 1.0)
    control, crb, cextra = score_for_row(51, p, fr_sym)
    res = simulate(p, score, rb, extra, funding=(universe in ("U", "F")), frate=frate)
    ctl = simulate(p, control, crb, cextra, funding=(universe in ("U", "F")), frate=frate)
    m = _stats(res, p["C"], p["O"])
    r1 = np.diff(res["eq"]) / np.maximum(res["eq"][:-1], 1e-12)
    r0 = np.diff(ctl["eq"]) / np.maximum(ctl["eq"][:-1], 1e-12)
    m["control_corr"] = round(float(np.corrcoef(r1, r0)[0, 1]), 6) if len(r1) > 3 else None
    # cost sensitivity and zero control on the same signals
    for bps, key in ((14.0, "rt14"), (22.0, "rt22"), (0.0, "zero")):
        rr = simulate(p, score, rb, extra, fee_bps=bps,
                      funding=(universe in ("U", "F") and bps != 0.0), frate=frate)
        m[f"net_{key}_pct"] = round(float((rr["eq"][-1] / INIT - 1) * 100), 4)
    m.update(dict(row=row, universe=universe, symbols=len(syms),
                  fee_bps_per_side=FEE, slippage_bps_per_side=SLIP,
                  cost_bp_roundtrip=2 * (FEE + SLIP),
                  funding_charged=universe in ("U", "F"),
                  bars=int(len(p["ts"])),
                  window_start_utc=str(pd.to_datetime(p["ts"][0], unit="ms", utc=True)),
                  window_end_utc=str(pd.to_datetime(p["ts"][-1], unit="ms", utc=True))))
    gates = dict(g1_n=m["n_trades"] >= 100,
                 g2_pf=m["profit_factor"] is not None and m["profit_factor"] > 1.2,
                 g3_net=m["net_pct"] > 0,
                 g4_folds=m["folds_total"] > 0 and
                 m["folds_profitable"] / m["folds_total"] >= 0.70,
                 g5_months=m["months_green_pct"] is not None and
                 m["months_green_pct"] >= 60.0,
                 g6_boot=m["boot_exp_lb"] is not None and m["boot_exp_lb"] > 0,
                 g7_dd=m["dd_p95_pct"] < 35.0)
    m["gates"] = gates
    m["gate_pass"] = all(gates.values())
    m["dsr_proxy"] = round(float(
        (np.diff(res["eq"]) / np.maximum(res["eq"][:-1], 1e-12)).mean() /
        max(float((np.diff(res["eq"]) / np.maximum(res["eq"][:-1], 1e-12)).std()), 1e-12) *
        np.sqrt(len(res["eq"])) -
        np.sqrt(2 * np.log(50))), 6)
    prov = dict(adapter="nontrend50", engine_version="nontrend50-1", row=row,
                universe=universe, n_symbols=len(syms),
                definition="Downloads/Non-Trend 50-Strategy Suite (#51–100)-claude.md")
    tables = [dict(kind="equity", i=int(i), v=float(v))
              for i, v in enumerate(res["eq"][::max(1, len(res["eq"]) // 500)])]
    return m, prov, tables


if __name__ == "__main__":
    print("nontrend50: run via vrun.py / code/_nontrend50_audit.py")
