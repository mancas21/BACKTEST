#!/usr/bin/env python
r"""
ml4tfund_engine.py -- the ML4T "Crypto Perpetuals Funding" book, ported.

Spec: results/ml4tfund_pre_registration.md (frozen 2026-11-22, before the
first market run). Source: case_studies/crypto_perps_funding/ in
stefan-jansen/machine-learning-for-trading.

WHAT THIS IS
------------
An eight-hour, funding-aligned, cross-sectional long-short book over the
nineteen Binance USD-M perpetuals the case study declares. At every settlement
stamp T it ranks the eligible contracts by funding (primary) or by the
fourteen-day funding z-score (secondary), goes long the k lowest and short the
k highest, equal weight within each side, and charges the funding it actually
paid plus the case study's transaction cost. It is the mechanism replica: the
published ML layer (44 features, GBM/LSTM/TCN) is NOT reproduced, and the spec
says why.

CONVENTIONS (all copied from the source, none invented)
-------------------------------------------------------
* Clock: 8h stamps 00/08/16 UTC. Timestamps floored to the second first --
  part of the store's funding history is stamped 08:00:00.001, and an exact
  modulo test silently drops whole years of it.
* Eligibility at T: a settlement exists at exactly T AND a 1h bar opens at
  exactly T. MKR's funding stops 2025-09-08 (delisting), so MKR leaves the
  panel there instead of being charged zero.
* Selection: k_eff = min(k, n // 2) names a side (utils/allocation.py). Fewer
  than two eligible names -> flat, the stamp is counted as skipped.
* Weights: equal WITHIN each side, long side sums to +1 and short side to -1,
  i.e. gross 2.0, net 0 (utils/allocation.py::_equal_weight_rows). NOT the
  repo's own gross-1 convention: this book is the case study's.
* Fill: open(T). The old book is closed and the new one opened at the same
  price, cost charged on sum|w_new - w_old_drifted|, where w_old_drifted is
  the previous target carried through the period's return.
* Funding: a position held over (T, T+8h] is charged EVERY settlement in that
  half-open window, summed -- not just the settlement at T+8h. SOL settles at
  4h/2h spacing for 75 settlements in November 2022; assuming one payment per
  window would half-charge it. A long pays a positive rate, a short receives
  it: pnl_i = w_i * (price_return_i - funding_sum_i).
* Costs, per leg on traded notional:
    cs_engine = 5 bps everywhere  (config/backtest/base.yaml: 4 commission
               + 1 slippage, the engine's production schedule)
    cs_tiered = majors 2 bps, alts 4 bps (setup.yaml costs.fee_schedule and
               features.majors: BTC ETH BNB SOL XRP are the five majors)
  A zero-cost path is computed INSIDE every artifact so the drag is measured,
  never derived.
* Sharpe: 8h returns compounded into UTC-daily returns, annualised with
  sqrt(365) (setup.yaml evaluation.periods_per_year). Crypto trades 7d/wk.
* No stop, no target, no volatility scaling, no leverage cap, no cash yield:
  the case study's baseline has none of them at this stage.

THE LEDGER
----------
weights `w` are SIGNED fractions of equity (+long, -short) and are used as-is
everywhere. Per period:

    cost_cash    = eq * sum_i cost_i * |w_new_i - w_old_i|
    eq_after     = eq - cost_cash
    price_cash   = eq_after * sum_i w_i * ret_i
    funding_cash = -eq_after * sum_i w_i * fund_i        (long pays positive)
    eq_next      = eq_after + price_cash + funding_cash

so `eq_next - eq == price_cash + funding_cash - cost_cash` exactly. The
accumulated version of that identity is asserted and published
(`pnl_identity_resid`). The sign of the short leg is pinned by known answers
B and C, because the repo has already paid once for a double-signed quantity
(xsml v1).

KNOWN ANSWERS: `python code/ml4tfund_engine.py` -- all must PASS before a
real-data run. `run_symbol` re-runs them and refuses if any fails.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ENGINE_VERSION = "ml4tfund-1"
INIT = 100_000.0
BAR_MS = 28_800_000                       # 8h
MAJORS = {"BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"}
UNIVERSE = ["AAVEUSDT", "ADAUSDT", "APTUSDT", "ATOMUSDT", "AVAXUSDT",
            "BNBUSDT", "BTCUSDT", "COMPUSDT", "DOGEUSDT", "DOTUSDT",
            "ETHUSDT", "INJUSDT", "LINKUSDT", "MKRUSDT", "NEARUSDT",
            "SOLUSDT", "SUIUSDT", "UNIUSDT", "XRPUSDT"]
COST_MODES = {
    "cs_engine": lambda sym: 5.0e-4,                                  # per leg
    "cs_tiered": lambda sym: 2.0e-4 if sym in MAJORS else 4.0e-4,     # per leg
    "zero": lambda sym: 0.0,
}
WINDOWS = {
    "val": ("2022-01-01", "2023-12-31"),      # the case study's two 1Y folds
    "holdout": ("2024-01-01", "2025-12-31"),  # their declared holdout
    "ext": ("2026-01-01", "2026-11-02"),      # beyond their history
}
Z_LOOKBACK = 42
Z_MIN = 21


# ─────────────────────────────────── data ──────────────────────────────────
def _load_inputs(paths):
    """Split the served inputs by extension and return raw per-symbol arrays."""
    bars, funds = {}, {}
    for p in paths:
        base = os.path.basename(p)
        if base.endswith("_1h.csv"):
            sym = base[:-len("_1h.csv")]
            df = pd.read_csv(p)
            df.columns = [str(c).strip().lower() for c in df.columns]
            t = df["open_ts"].to_numpy(np.int64)
            o = df["open"].to_numpy(float)
            order = np.argsort(t, kind="stable")
            t, o = t[order], o[order]
            keep = np.concatenate([[True], np.diff(t) > 0])
            bars[sym] = (t[keep], o[keep])
        elif base.endswith("_funding.json"):
            sym = base[:-len("_funding.json")]
            with open(p, encoding="utf-8") as fh:
                recs = json.load(fh)
            # floor to the SECOND: the store carries .001/.004/.011 offsets
            t = np.array([int(r["t"]) // 1000 * 1000 for r in recs], np.int64)
            r = np.array([float(r["r"]) for r in recs], float)
            order = np.argsort(t, kind="stable")
            t, r = t[order], r[order]
            keep = np.concatenate([[True], np.diff(t) > 0])
            funds[sym] = (t[keep], r[keep])
    missing = [s for s in UNIVERSE if s not in bars or s not in funds]
    if missing:
        raise ValueError(f"inputs missing for universe members: {missing}")
    return bars, funds


def _grid(funds):
    """8h stamps that carry at least one settlement."""
    stamps = set()
    for t, _ in funds.values():
        stamps.update(int(x) for x in t if int(x) % BAR_MS == 0)
    return np.array(sorted(stamps), np.int64)


def _matrices(grid, bars, funds, symbols):
    n, s = len(grid), len(symbols)
    P = np.full((n, s), np.nan)
    Fa = np.full((n, s), np.nan)
    Fs = np.zeros((n, s))
    for j, sym in enumerate(symbols):
        bt, bo = bars[sym]
        k = np.searchsorted(bt, grid)
        ok = (k < len(bt)) & (bt[np.clip(k, 0, len(bt) - 1)] == grid)
        P[ok, j] = bo[k[ok]]
        ft, fr = funds[sym]
        k = np.searchsorted(ft, grid)
        ok = (k < len(ft)) & (ft[np.clip(k, 0, len(ft) - 1)] == grid)
        Fa[ok, j] = fr[k[ok]]
        cum = np.concatenate([[0.0], np.cumsum(fr)])
        idx = np.searchsorted(ft, grid, side="right")
        Fs[:-1, j] = cum[idx[1:]] - cum[idx[:-1]]
        Fs[-1, j] = 0.0
    return P, Fa, Fs


def _scores(Fa, score):
    """Trailing score per stamp, computed only from settlements at or before it."""
    if score == "level":
        return -Fa
    if score != "z":
        raise ValueError(f"unknown score {score!r}")
    z = np.full_like(Fa, np.nan)
    for j in range(Fa.shape[1]):
        col = Fa[:, j]
        have = np.flatnonzero(np.isfinite(col))
        if len(have) < Z_MIN:
            continue
        vals = col[have]
        cs = np.concatenate([[0.0], np.cumsum(vals)])
        cs2 = np.concatenate([[0.0], np.cumsum(vals * vals)])
        for i in range(Z_MIN - 1, len(have)):
            lo = max(0, i + 1 - Z_LOOKBACK)
            m = i + 1 - lo
            mean = (cs[i + 1] - cs[lo]) / m
            var = (cs2[i + 1] - cs2[lo]) / m - mean * mean
            sd = np.sqrt(max(var, 0.0))
            if sd > 1e-12:
                z[have[i], j] = -(vals[i] - mean) / sd
    return z


# ─────────────────────────────────── book ──────────────────────────────────
def _run_book(grid, P, Fa, Fs, symbols, *, k, cost_per_leg, score="level",
              init=INIT, start=None, end=None):
    """Run the book over grid[start:end+1]; return metrics + tables."""
    S = list(symbols)
    cost = np.asarray([cost_per_leg(s) for s in S], float)
    sc = _scores(Fa, score)
    lo = 0 if start is None else max(int(start), 0)
    hi = len(grid) - 1 if end is None else min(int(end), len(grid) - 1)

    eq = init
    w = np.zeros(len(S))
    curve = [eq]
    t_ms = [int(grid[lo])]
    per_ret, per_cost, per_fund, per_price, per_turn, per_names = [], [], [], [], [], []
    legs = []
    contrib = np.zeros(len(S))
    contrib_f = np.zeros(len(S))
    contrib_p = np.zeros(len(S))
    leg_cnt = np.zeros(len(S), int)
    leg_win = np.zeros(len(S), int)
    side_net = {"long": 0.0, "short": 0.0}
    side_f = {"long": 0.0, "short": 0.0}
    side_p = {"long": 0.0, "short": 0.0}
    n_flat = 0
    charged = 0
    spread_bps, ics, gross = [], [], []

    for t in range(lo, hi):
        px0, px1 = P[t], P[t + 1]
        idx = np.flatnonzero(np.isfinite(px0) & np.isfinite(Fa[t]))
        target = np.zeros(len(S))
        keff = 0
        if len(idx) >= 2:
            s = sc[t, idx]
            good = np.isfinite(s)
            idx, s = idx[good], s[good]
        if len(idx) >= 2:
            keff = min(int(k), len(idx) // 2)
        if keff >= 1:
            order = idx[np.lexsort((idx, -s))]
            longs, shorts = order[:keff], order[-keff:]
            target[longs] = 1.0 / keff
            target[shorts] = -1.0 / keff
            spread_bps.append(float(np.mean(Fa[t, shorts]) * 1e4
                                    - np.mean(Fa[t, longs]) * 1e4))

        traded = np.abs(target - w)
        cost_cash = eq * float(np.sum(cost * traded))
        eq_after = eq - cost_cash
        ret = np.zeros(len(S))
        ok = np.isfinite(px0) & np.isfinite(px1) & (px0 > 0)
        ret[ok] = px1[ok] / px0[ok] - 1.0
        fund = np.where(np.isfinite(px0), Fs[t], 0.0)
        pnl_i = target * (ret - fund)
        port = float(np.sum(pnl_i))
        price_cash = eq_after * float(np.sum(target * ret))
        fund_cash = -eq_after * float(np.sum(target * fund))
        eq_next = eq_after + price_cash + fund_cash

        if keff >= 1 and len(idx) >= 3:
            a = pd.Series(sc[t, idx]).rank().to_numpy()
            b = pd.Series(ret[idx]).rank().to_numpy()
            if a.std() > 0 and b.std() > 0:
                ics.append(float(np.corrcoef(a, b)[0, 1]))

        if keff >= 1:
            for j in np.flatnonzero(target):
                pnl = float(eq_after * target[j] * (ret[j] - fund[j]))
                legs.append((int(grid[t]), S[j], pnl))
                leg_cnt[j] += 1
                leg_win[j] += int(pnl > 0)
                contrib[j] += pnl
                contrib_f[j] += -eq_after * target[j] * fund[j]
                contrib_p[j] += eq_after * target[j] * ret[j]
                side = "long" if target[j] > 0 else "short"
                side_net[side] += pnl
                side_f[side] += -eq_after * target[j] * fund[j]
                side_p[side] += eq_after * target[j] * ret[j]
            charged += int(np.sum(fund[target != 0] != 0.0))
        gross.append(float(np.sum(np.abs(target))))

        if keff >= 1 and abs(1.0 + port) > 1e-12:
            w = target * (1.0 + pnl_i) / (1.0 + port)
        else:
            w = target

        per_ret.append((eq_next - eq) / eq if eq else port)
        per_cost.append(cost_cash)
        per_fund.append(fund_cash)
        per_price.append(price_cash)
        per_turn.append(float(np.sum(traded)))
        per_names.append(len(idx))
        if keff < 1:
            n_flat += 1
        eq = eq_next
        curve.append(eq)
        t_ms.append(int(grid[t + 1]))
        if eq <= 0:
            break

    curve = np.asarray(curve, float)
    r = np.asarray(per_ret, float)
    stamps = pd.to_datetime(np.asarray(t_ms, np.int64), unit="ms", utc=True)
    pend = stamps[1:]
    days = max((stamps[-1] - stamps[0]).total_seconds() / 86400.0, 1e-9)
    daily = pd.Series(1.0 + r, index=pend).groupby(pend.normalize()).prod() - 1.0
    dv = daily.to_numpy(float)
    sd = float(np.std(dv, ddof=1)) if len(dv) > 1 else 0.0
    sharpe = float(np.mean(dv) / sd * np.sqrt(365.0)) if sd > 0 else 0.0
    neg = dv[dv < 0]
    dsd = float(np.std(neg, ddof=1)) if len(neg) > 1 else 0.0
    sortino = float(np.mean(dv) / dsd * np.sqrt(365.0)) if dsd > 0 else 0.0
    peak = np.maximum.accumulate(curve)
    mdd = float((curve / peak - 1.0).min()) * 100.0
    tot = curve[-1] / init - 1.0
    cagr = ((curve[-1] / init) ** (365.0 / days) - 1.0) * 100.0 if curve[-1] > 0 else -100.0

    leg_pnl = np.array([x[2] for x in legs], float)
    gp = float(leg_pnl[leg_pnl > 0].sum()) if len(leg_pnl) else 0.0
    gl = float(-leg_pnl[leg_pnl < 0].sum()) if len(leg_pnl) else 0.0
    pp = float(r[r > 0].sum())
    pn = float(-r[r < 0].sum())

    cost_total = float(np.sum(per_cost))
    fund_total = float(np.sum(per_fund))
    price_total = float(np.sum(per_price))
    resid = float(curve[-1] - (init + price_total + fund_total - cost_total))

    m = dict(
        return_pct=100.0 * tot, final_equity=float(curve[-1]), cagr_pct=float(cagr),
        sharpe=sharpe, sortino=sortino, max_dd_pct=float(mdd),
        calmar=float(cagr / abs(mdd)) if mdd < 0 else 0.0,
        n_trades=int(len(legs)), win_rate=float(leg_win.sum() / max(leg_cnt.sum(), 1)),
        profit_factor=float(gp / gl) if gl > 0 else (99.0 if gp > 0 else 0.0),
        period_profit_factor=float(pp / pn) if pn > 0 else (99.0 if pp > 0 else 0.0),
        n_periods=int(len(r)), n_rebalances=int(len(r) - n_flat),
        n_flat_periods=int(n_flat), days=float(days), n_daily=int(len(dv)),
        funding_pct=float(100.0 * fund_total / init),
        price_pct=float(100.0 * price_total / init),
        cost_pct=float(100.0 * cost_total / init),
        cost_bps_per_year=float(100.0 * cost_total / init * 1e4 / days * 365.0),
        turnover_per_rebal=float(np.mean(per_turn)) if per_turn else 0.0,
        turnover_per_year=float(np.sum(per_turn) / days * 365.0) if per_turn else 0.0,
        avg_names=float(np.mean(per_names)) if per_names else 0.0,
        min_names=int(np.min(per_names)) if per_names else 0,
        max_names=int(np.max(per_names)) if per_names else 0,
        traded_share=float(np.mean(np.asarray(per_names) >= 2)) if per_names else 0.0,
        avg_gross=float(np.mean(gross)) if gross else 0.0,
        mean_funding_spread_bps=float(np.mean(spread_bps)) if spread_bps else 0.0,
        mean_funding_spread_bps_year=float(np.mean(spread_bps) * 3 * 365) if spread_bps else 0.0,
        rank_ic_mean=float(np.nanmean(ics)) if ics else 0.0,
        pct_positive_periods=float((r > 0).mean() * 100.0) if len(r) else 0.0,
        best_period_pct=float(r.max() * 100.0) if len(r) else 0.0,
        worst_period_pct=float(r.min() * 100.0) if len(r) else 0.0,
        position_settlements_charged=int(charged),
        pnl_identity_resid=resid,
        ruin=bool(curve[-1] <= 0),
    )
    m["flag"] = "OK" if m["n_periods"] >= 250 else "INSUFFICIENT_SAMPLE"

    by_year = []
    yrs = pend.year.to_numpy()
    rarr = np.asarray(per_ret, float)
    for y in sorted(set(int(x) for x in yrs)):
        sel = yrs == y
        yy = daily[daily.index.year == y].to_numpy(float)
        sdy = float(np.std(yy, ddof=1)) if len(yy) > 1 else 0.0
        by_year.append(dict(
            id=f"y{y}", kind="year", year=int(y), periods=int(sel.sum()),
            ret_pct=float((np.prod(1.0 + rarr[sel]) - 1.0) * 100.0),
            sharpe=float(np.mean(yy) / sdy * np.sqrt(365.0)) if sdy > 0 else 0.0,
            funding_pct=float(100.0 * np.sum(np.asarray(per_fund)[sel]) / init),
            price_pct=float(100.0 * np.sum(np.asarray(per_price)[sel]) / init),
            cost_pct=float(100.0 * np.sum(np.asarray(per_cost)[sel]) / init),
            avg_names=float(np.mean(np.asarray(per_names)[sel])),
            turnover=float(np.mean(np.asarray(per_turn)[sel])),
        ))

    by_symbol = []
    for j, sym in enumerate(S):
        if leg_cnt[j] == 0:
            continue
        by_symbol.append(dict(
            id=str(sym), kind="symbol", symbol=str(sym), legs=int(leg_cnt[j]),
            win_rate=float(leg_win[j] / leg_cnt[j]),
            net_pct=float(100.0 * contrib[j] / init),
            funding_pct=float(100.0 * contrib_f[j] / init),
            price_pct=float(100.0 * contrib_p[j] / init),
        ))
    by_symbol.sort(key=lambda x: x["net_pct"])

    sides = [dict(id=side, kind="side", side=side,
                  net_pct=float(100.0 * side_net[side] / init),
                  funding_pct=float(100.0 * side_f[side] / init),
                  price_pct=float(100.0 * side_p[side] / init))
             for side in ("long", "short")]

    tables = [dict(id="cell", kind="cell",
                   **{kk: m[kk] for kk in
                      ("return_pct", "cagr_pct", "sharpe", "sortino",
                       "max_dd_pct", "funding_pct", "price_pct", "cost_pct",
                       "turnover_per_rebal", "n_periods", "n_trades",
                       "avg_names", "rank_ic_mean", "mean_funding_spread_bps")}),
              *by_year, *sides, *by_symbol]
    return m, tables


# ───────────────────────────────── adapter entry ───────────────────────────
def run_symbol(paths, params):
    p = dict(params)
    window = str(p.pop("window", "holdout"))
    k = int(p.pop("k", 5))
    cost_mode = str(p.pop("cost", "cs_engine"))
    score = str(p.pop("score", "level"))
    init = float(p.pop("init", INIT))
    skip_audit = bool(int(p.pop("skip_audit", 0)))
    if p:
        raise ValueError(f"unknown ml4tfund params: {sorted(p)}")
    if window not in WINDOWS:
        raise ValueError(f"window must be one of {sorted(WINDOWS)}")
    if cost_mode not in COST_MODES:
        raise ValueError(f"cost must be one of {sorted(COST_MODES)}")
    if not skip_audit:
        if _selftest(verbose=False):
            raise RuntimeError("known answers FAILED -- refusing a real-data run")

    bars, funds = _load_inputs(paths)
    grid = _grid(funds)
    P, Fa, Fs = _matrices(grid, bars, funds, UNIVERSE)
    d = pd.to_datetime(grid, unit="ms", utc=True)
    a, b = WINDOWS[window]
    mask = (d >= pd.Timestamp(a, tz="UTC")) & (d < pd.Timestamp(b, tz="UTC")
                                               + pd.Timedelta(days=1))
    idx = np.flatnonzero(mask)
    if len(idx) < 3:
        raise ValueError(f"window {window} has only {len(idx)} stamps")
    start, end = int(idx[0]), int(idx[-1])

    m, tables = _run_book(grid, P, Fa, Fs, UNIVERSE, k=k,
                          cost_per_leg=COST_MODES[cost_mode], score=score,
                          init=init, start=start, end=end)
    mz, _ = _run_book(grid, P, Fa, Fs, UNIVERSE, k=k,
                      cost_per_leg=COST_MODES["zero"], score=score,
                      init=init, start=start, end=end)
    m["return_zero_pct"] = mz["return_pct"]
    m["sharpe_zero"] = mz["sharpe"]
    m["drag_pp"] = mz["return_pct"] - m["return_pct"]
    m["window"] = window
    m["k"] = k
    m["cost_mode"] = cost_mode
    m["score"] = score
    m["universe_size"] = len(UNIVERSE)
    m["gate_g4_costs_bind"] = bool(mz["sharpe"] > m["sharpe"])
    m["gate_g5_funding_positive"] = bool(m["funding_pct"] > 0)
    m["gate_g6_traded"] = bool(m["traded_share"] >= 0.95)
    m["gate_g7_identity"] = bool(abs(m["pnl_identity_resid"]) < 1e-6 * init)

    prov = {"adapter": "ml4tfund", "engine_version": ENGINE_VERSION,
            "source": "ML4T case_studies/crypto_perps_funding",
            "score": score, "k": k, "cost": cost_mode, "window": window}
    return m, prov, tables


# ───────────────────────────────── known answers ───────────────────────────
def _gridn(n, base=1_577_836_800_000):
    """Aligned 8h grid: 2020-01-01T00:00Z, 08:00Z, 16:00Z, ... (3 stamps/day)."""
    return np.array([base + i * BAR_MS for i in range(n)], np.int64)


def _case(name, got, expect, tol=1e-9):
    bad = []
    for kk, v in expect.items():
        g = got.get(kk)
        if isinstance(v, float):
            if g is None or abs(float(g) - v) > tol * max(1.0, abs(v)):
                bad.append(f"{kk}: got {g!r} want {v!r}")
        elif g != v:
            bad.append(f"{kk}: got {g!r} want {v!r}")
    return (not bad), (name if not bad else f"{name} -- " + "; ".join(bad))


def _selftest(verbose=True):
    """Hand-computed expectations for every rule that can move money.

    A failure here is the TEST's fault until proven otherwise: every case was
    re-derived by hand before the first real-data run (2026-11-22).
    """
    res = []
    g3 = _gridn(3)
    syms = ["AAA", "BBB"]
    flat = np.array([[100.0, 100.0]] * 3)
    Fa = np.array([[1e-4, 3e-4]] * 3)
    Fs = np.array([[1e-4, 3e-4], [1e-4, 3e-4], [0.0, 0.0]])

    # A. carry, flat prices, engine cost, ONE period (no drift to rebalance).
    #    long AAA pays 1e-4, short BBB receives 3e-4 -> funding +2e-4 on 999
    #    after a 1e-3 turnover cost.
    g2 = _gridn(2)
    FsA = np.array([[1e-4, 3e-4], [0.0, 0.0]])
    m, _ = _run_book(g2, flat[:2], Fa[:2], FsA, syms, k=1,
                     cost_per_leg=lambda s: 5e-4, init=1000.0)
    res.append(_case("A carry + engine cost", m, dict(
        return_pct=100.0 * (999.0 * 1.0002 / 1000.0 - 1.0),
        funding_pct=100.0 * 0.1998 / 1000.0,
        price_pct=0.0, cost_pct=100.0 * 1.0 / 1000.0,
        n_periods=1, n_trades=2)))

    # B. both prices +10%: a +1/-1 book earns exactly ZERO on price, so a
    #    double-signed short (the xsml v1 defect) cannot pass this.
    P2 = np.array([[100.0, 100.0], [110.0, 110.0], [121.0, 121.0]])
    Fs0 = np.zeros((3, 2))
    m, _ = _run_book(g3, P2, Fa, Fs0, syms, k=1,
                     cost_per_leg=lambda s: 0.0, init=1000.0)
    res.append(_case("B short-leg sign", m,
                     dict(price_pct=0.0, return_pct=0.0)))

    # C. one name -> k_eff = 0 -> flat, no cost, nothing traded
    m, _ = _run_book(g3, flat[:, :1], Fa[:, :1], Fs[:, :1], ["AAA"], k=1,
                     cost_per_leg=lambda s: 5e-4, init=1000.0)
    res.append(_case("C one name -> flat", m,
                     dict(return_pct=0.0, n_trades=0, n_periods=2,
                          n_flat_periods=2, traded_share=0.0)))

    # D. three names, k=2 -> k_eff = min(2, 1) = 1 -> two legs per period
    P3 = np.array([[100.0] * 3] * 3)
    Fa3 = np.array([[1e-4, 2e-4, 3e-4]] * 3)
    Fs3 = np.array([[1e-4, 2e-4, 3e-4]] * 2 + [[0.0] * 3])
    m, _ = _run_book(g3, P3, Fa3, Fs3, ["A", "B", "C"], k=2,
                     cost_per_leg=lambda s: 0.0, init=1000.0)
    res.append(_case("D k_eff clamp", m, dict(n_trades=4, avg_names=3.0)))

    # E. TWO settlements inside one window must both be charged: the window
    #    carries 6e-4 while the stamp's own rate is 1e-4.
    Fs_multi = np.array([[6e-4, 0.0], [0.0, 0.0], [0.0, 0.0]])
    P_two = np.array([[100.0, 100.0]] * 3)
    m, _ = _run_book(g3, P_two, Fa, Fs_multi, syms, k=1,
                     cost_per_leg=lambda s: 0.0, init=1000.0)
    res.append(_case("E funding summed in window", m,
                     dict(funding_pct=100.0 * (-0.6) / 1000.0)))

    # F. tiered cost: AAA 2 bps + BBB 4 bps on 1.0 notional each = 6e-4
    m, _ = _run_book(g3, flat, Fa, Fs0, syms, k=1,
                     cost_per_leg=lambda s: 2e-4 if s == "AAA" else 4e-4,
                     init=1000.0)
    res.append(_case("F tiered cost", m,
                     dict(cost_pct=100.0 * 0.6 / 1000.0)))

    # G. turnover is measured on the DRIFTED book: AAA +10%, BBB flat ->
    #    drifted short weight -1/1.1 = -0.9091, so the next rebalance trades
    #    0.0909, not 0.
    P4 = np.array([[100.0, 100.0], [110.0, 100.0], [121.0, 100.0]])
    m, _ = _run_book(g3, P4, Fa, Fs0, syms, k=1,
                     cost_per_leg=lambda s: 0.0, init=1000.0)
    # period 1: +10% on the long leg -> 1100; period 2: +10% again
    res.append(_case("G drift + long leg", m, dict(
        price_pct=100.0 * (100.0 + 110.0) / 1000.0,
        turnover_per_rebal=float((2.0 + (1.0 - 1.0 / 1.1)) / 2.0))))

    # H. the z ranking and the level ranking must pick DIFFERENT shorts.
    #    AAA sits at 1e-4 and spikes to 4e-4 (z high, level low); BBB sits at
    #    1e-3 (level high, z ~ 0). Level shorts BBB; z shorts AAA.
    n = 25
    gH = _gridn(n)
    PH = np.full((n, 2), 100.0)
    PH[-1, 0] = 110.0                       # AAA +10% in the last period
    FH = np.zeros((n, 2))
    FH[:, 0] = 1e-4
    FH[-2:, 0] = 4e-4
    FH[:, 1] = 1e-3 + 1e-5 * (np.arange(n) % 2)
    FH[-1, 1] = 1e-3
    FsH = np.zeros((n, 2))
    ml, tl = _run_book(gH, PH, FH, FsH, syms, k=1, score="level",
                       cost_per_leg=lambda s: 0.0, init=1000.0)
    mz, tz = _run_book(gH, PH, FH, FsH, syms, k=1, score="z",
                       cost_per_leg=lambda s: 0.0, init=1000.0)
    al = {x["symbol"]: x["net_pct"] for x in tl if x["kind"] == "symbol"}
    az = {x["symbol"]: x["net_pct"] for x in tz if x["kind"] == "symbol"}
    ok = (al.get("AAA", 0.0) > 0 > az.get("AAA", 0.0))
    res.append((ok, "H level vs z pick different shorts"
                + ("" if ok else f" -- level AAA {al.get('AAA')} z AAA {az.get('AAA')}")))

    # I. accumulated accounting identity (equity == init + price + funding - cost)
    m, _ = _run_book(g3, P4, Fa, Fs, syms, k=1,
                     cost_per_leg=lambda s: 5e-4, init=1000.0)
    res.append(_case("I accounting identity", m, dict(pnl_identity_resid=0.0)))

    # J. Sharpe = sqrt(365) on UTC-DAILY compounded 8h returns. Two days:
    #    three periods at +1% then three at +2%. The long leg carries the
    #    price move, the short leg is flat.
    gJ = _gridn(7)
    pJ = np.array([[100.0, 100.0]])
    a = [100.0 * 1.01 ** i for i in range(4)]
    b = [a[-1] * 1.02 ** i for i in range(1, 4)]
    colA = np.array(a + b)
    PJ = np.column_stack([colA, np.full(7, 100.0)])
    FaJ = np.full((7, 2), 1e-4)
    FsJ = np.zeros((7, 2))
    m, _ = _run_book(gJ, PJ, FaJ, FsJ, syms, k=1,
                     cost_per_leg=lambda s: 0.0, init=1000.0)
    # independent reimplementation of the daily grouping: a period belongs to
    # the UTC day of its END stamp, and the three (or two) periods of a day
    # compound into that day's return.
    rets = np.diff(colA) / colA[:-1]
    ends = pd.to_datetime(gJ[1:], unit="ms", utc=True)
    buckets = {}
    for t, x in zip(ends, rets):
        buckets.setdefault(t.date(), []).append(1.0 + float(x))
    dv = np.array([np.prod(v) - 1.0 for v in buckets.values()])
    want = float(np.mean(dv) / np.std(dv, ddof=1) * np.sqrt(365.0))
    res.append(_case("J annualisation", m,
                     dict(sharpe=want, n_daily=len(dv)), tol=1e-12))

    fails = sum(1 for ok, _ in res if not ok)
    if verbose:
        for ok, name in res:
            print(f"{'PASS' if ok else 'FAIL'} {name}")
        print(f"\n{len(res)} known answers, {fails} FAIL")
    return fails


if __name__ == "__main__":
    raise SystemExit(1 if _selftest() else 0)
