#!/usr/bin/env python
"""9-21 EMA crossover — repo port with funding, repo costs and an asserted
accounting identity.

SOURCE OF RECORD
    code/ema921_source.py, a byte-identical copy of
    `Downloads/ema_9_21_backtest-claude.py`
    (sha256 8be0020d057a4ef73fbed9e4ab4f11b97d131f3d62b3094f47e6ded80a2189c4).
    The source is a complete single-file backtest, so the port keeps its loop
    and its execution rules and adds only what the repo requires of every
    perpetual book.

RULES (verbatim from the source)
    Trend    EMA(9) vs EMA(21), Pine-style seeding (SMA of the first n bars).
    Signal   EMA9 crosses EMA21 on the bar close.
    Entry    NEXT bar open, +/- slippage.
    Stop     long: rolling 10-bar low at the SIGNAL bar minus `sl_atr_buffer`
             x ATR(14) (default buffer 0 -> raw swing); short: mirror.
    Target   entry +/- rr x risk, rr = 2.0, use_tp = true.
    Exit     close crossing the slow EMA (exit_mode "price_slow"), TP, SL, or
             an opposite crossover (which closes and flips).
    Filter   skip the trade when the SL distance is < min_sl_pct (0.10 %) of
             entry.
    Sizing   risk_pct (1 %) of equity over the SL distance, capped at
             max_leverage (5x); compounding. One position at a time.

DECLARED ADDITIONS (the source has none of these)
    * COSTS are injected by the caller. Default repo regime: 5.0 bps fee +
      0.5 bps slippage per side = 11 bps round trip. The source's own
      4.0/1.0 is run as a declared sensitivity in the parity check only.
    * FUNDING is charged at the REAL settlement instants on the notional held
      at the settlement, marked at the open of the first bar that opens at or
      after it. A 1d bar therefore charges a mid-day settlement at the next
      daily open (declared; the repo's intraday books are exact).
    * The replayed window STARTS at the first funding settlement when a
      funding file exists, so no bar is charged zero funding by omission.
      `funding_covers_bars` measures the covered fraction of the replayed
      window and the audit requires it to be 1.0.
    * `eq[-1] - INIT == sum(trade.pnl)` is ASSERTED inside every run; the
      residual is published as `pnl_identity_resid`.

Known answers: code/_ema921_audit.py (both directions, every execution rule).
Parity vs the source: code/_ema921_parity.py.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

MIN_TRADE_FLAG = 30


# --------------------------------------------------------------------------- #
# Params
# --------------------------------------------------------------------------- #
@dataclass
class Params:
    fast: int = 9
    slow: int = 21
    allow_long: bool = True
    allow_short: bool = True

    swing_lookback: int = 10
    sl_atr_buffer: float = 0.0
    atr_len: int = 14
    min_sl_pct: float = 0.10

    rr: float = 2.0
    use_tp: bool = True
    exit_mode: str = "price_slow"

    adx_min: float = 0.0
    adx_len: int = 14
    min_spread_pct: float = 0.0

    fee_bps: float = 5.0
    slip_bps: float = 0.5
    risk_pct: float = 1.0
    max_leverage: float = 5.0
    initial_equity: float = 10_000.0

    funding: bool = True


def params_from(d: dict | None) -> Params:
    d = dict(d or {})
    d.pop("tf", None)          # injected by the harness, not an engine knob
    known = {f for f in Params.__dataclass_fields__}
    unknown = set(d) - known
    if unknown:
        raise ValueError(f"unknown params: {sorted(unknown)}")
    return Params(**d)


# --------------------------------------------------------------------------- #
# Indicators (Pine-style: EMA/RMA seeded with SMA)
# --------------------------------------------------------------------------- #
def ema(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    out[n - 1] = x[:n].mean()
    a = 2.0 / (n + 1)
    for i in range(n, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def rma(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    valid = np.where(~np.isnan(x))[0]
    if len(valid) == 0:
        return out
    k = valid[0]
    if len(x) < k + n:
        return out
    out[k + n - 1] = x[k:k + n].mean()
    for i in range(k + n, len(x)):
        out[i] = (out[i - 1] * (n - 1) + x[i]) / n
    return out


def true_range(h, l, c):
    tr = np.empty(len(c))
    tr[0] = h[0] - l[0]
    pc = c[:-1]
    tr[1:] = np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - pc),
                                np.abs(l[1:] - pc)])
    return tr


def atr_wilder(h, l, c, n):
    return rma(true_range(h, l, c), n)


def adx_wilder(h, l, c, n):
    up = np.zeros(len(c))
    dn = np.zeros(len(c))
    up[1:] = h[1:] - h[:-1]
    dn[1:] = l[:-1] - l[1:]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr_s = rma(true_range(h, l, c), n)
    pdi = 100 * rma(pdm, n) / tr_s
    mdi = 100 * rma(mdm, n) / tr_s
    dx = 100 * np.abs(pdi - mdi) / np.where((pdi + mdi) == 0, np.nan, pdi + mdi)
    return rma(dx, n)


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
def load_klines(path: str) -> pd.DataFrame:
    """Repo CSV (open_ts ms, open/high/low/close/volume) -> UTC-indexed frame."""
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    if "open_ts" in df.columns:
        idx = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
    elif "timestamp" in df.columns:
        idx = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    else:
        raise ValueError(f"{path}: no open_ts/timestamp column")
    out = df[["open", "high", "low", "close"]].astype(float)
    out.index = idx
    out = out.sort_index()
    out = out[~out.index.duplicated(keep="first")]
    return out


def load_funding(path: str):
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    t = np.array([int(r["t"]) for r in rows], dtype=np.int64)
    r = np.array([float(r["r"]) for r in rows], dtype=float)
    order = np.argsort(t)
    return t[order], r[order]


def funding_by_bar(open_ts_ms: np.ndarray, settle_ms: np.ndarray,
                   rate: np.ndarray, bar_ms: int | None = None
                   ) -> tuple[np.ndarray, dict]:
    """Rate charged at each bar's OPEN (the house convention).

    Same rule as `cbpack_funding_engine.attach_funding_events`: a settlement is
    charged to the bar that CONTAINS it (the last bar whose open <= T) and
    billed at that bar's open, before any fill at that open. For 1h/15m/5m/1m
    bars the 8h settlements land exactly on bar opens, so the rule is exact;
    a 1d bar holds three settlements and sums them at the daily open (declared
    approximation, also the house's).

    Settlements before the first bar are COUNTED, never charged; settlements
    at or beyond `last_open + bar_ms` are counted as after-window. Several
    settlements inside one bar are SUMMED, and the collapse is counted.
    """
    n = len(open_ts_ms)
    by_bar = np.zeros(n, dtype=float)
    stats = {"events": int(len(settle_ms)), "before_first": 0,
             "after_last": 0, "multi_bar_events": 0, "last_bar_events": 0}
    if n == 0 or len(settle_ms) == 0:
        return by_bar, stats
    if bar_ms is None:
        diffs = np.diff(open_ts_ms)
        bar_ms = int(np.median(diffs)) if len(diffs) else 0
    idx = np.searchsorted(open_ts_ms, settle_ms, side="right") - 1
    before = idx < 0
    after = (settle_ms >= open_ts_ms[-1] + bar_ms) if bar_ms > 0 \
        else np.zeros(len(settle_ms), bool)
    ok = (~before) & (~after)
    stats["before_first"] = int(before.sum())
    stats["after_last"] = int(after.sum())
    stats["multi_bar_events"] = int(ok.sum() - len(np.unique(idx[ok])))
    stats["last_bar_events"] = int((idx[ok] == n - 1).sum())
    np.add.at(by_bar, idx[ok], rate[ok])
    return by_bar, stats


def _index_to_ms(idx) -> np.ndarray:
    """DatetimeIndex -> epoch milliseconds, UNIT-INDEPENDENT.

    pandas 3 gives `to_datetime(..., unit="ms")` an index in microseconds (or
    seconds), so `asi8 // 10**6` silently produces SECONDS: every settlement
    then sorts after every bar and the funding trim eats the whole window
    (measured on the first BTC 1h run: 62,686 of 62,687 bars trimmed, zero
    trades). Normalize to ns first and assert the result is a plausible epoch.
    """
    ms = (idx.as_unit("ns").asi8 // 10**6).astype(np.int64)
    if len(ms):
        if not (1_000_000_000_000 <= int(ms[0]) <= 10_000_000_000_000):
            raise AssertionError(f"index->ms produced {int(ms[0])}, not an epoch in ms")
    return ms


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #
def run_backtest(df: pd.DataFrame, p: Params,
                 rate_by_bar: np.ndarray | None = None):
    o, h, l, c = (df[k].to_numpy(float)
                  for k in ("open", "high", "low", "close"))
    idx = df.index
    n = len(df)
    if rate_by_bar is None:
        rate_by_bar = np.zeros(n, dtype=float)

    fast = ema(c, p.fast)
    slow = ema(c, p.slow)
    atr = atr_wilder(h, l, c, p.atr_len)
    adx = adx_wilder(h, l, c, p.adx_len) if p.adx_min > 0 else None
    warm = max(p.slow, p.atr_len, 2 * p.adx_len) + 2

    fee = p.fee_bps / 1e4
    slip = p.slip_bps / 1e4
    equity = p.initial_equity
    eq_curve = np.full(n, np.nan)
    gross_curve = np.zeros(n, dtype=float)

    pos = 0
    qty = entry = sl = tp = risk_amt = entry_fee = 0.0
    entry_i = 0
    pend_exit = False
    pend_entry = 0
    pend_sl = np.nan
    pos_funding = 0.0
    funding_total = 0.0
    fees_total = 0.0
    trades: list[dict] = []

    def close_trade(i, px, reason):
        nonlocal pos, equity, qty, pos_funding, funding_total, fees_total
        exit_fee = qty * px * fee
        gross = qty * (px - entry) * pos
        net = gross - exit_fee - entry_fee - pos_funding
        # funding was already debited from equity at each settlement, and the
        # entry fee at the open: only the exit fee is new here.
        equity += gross - exit_fee
        funding_total += pos_funding
        fees_total += exit_fee
        trades.append(dict(
            entry_time=idx[entry_i], exit_time=idx[i],
            side="long" if pos == 1 else "short",
            entry=entry, exit=px, sl=sl, tp=tp, qty=qty, bars=i - entry_i,
            pnl=net, R=net / risk_amt if risk_amt else np.nan,
            reason=reason, equity=equity,
            fees=entry_fee + exit_fee, funding=pos_funding,
            notional=qty * entry,
        ))
        pos = 0
        qty = 0.0
        pos_funding = 0.0

    for i in range(n):
        # 0) funding settlement at this bar's open, on the position HELD at it
        if p.funding and pos and rate_by_bar[i] != 0.0:
            cost = pos * qty * o[i] * rate_by_bar[i]
            equity -= cost
            pos_funding += cost

        # 1) pending signal exit -> next open
        if pos and pend_exit:
            close_trade(i, o[i] * (1 - slip * pos), "signal")
        pend_exit = False

        # 2) pending entry -> next open
        if pos == 0 and pend_entry != 0:
            d = pend_entry
            px = o[i] * (1 + slip * d)
            risk_u = (px - pend_sl) * d
            if risk_u > 0 and risk_u / px * 100 >= p.min_sl_pct:
                qty = min(equity * p.risk_pct / 100 / risk_u,
                          equity * p.max_leverage / px)
                risk_amt = qty * risk_u
                entry_fee = qty * px * fee
                equity -= entry_fee
                fees_total += entry_fee
                pos, entry, sl, entry_i = d, px, pend_sl, i
                tp = px + d * p.rr * risk_u if p.use_tp else np.nan
                pos_funding = 0.0
        pend_entry = 0

        # 3) intrabar SL / TP
        if pos:
            d = pos
            if i > entry_i:  # gap through level at open
                if (o[i] - sl) * d <= 0:
                    close_trade(i, o[i], "SL_gap")
                elif p.use_tp and (o[i] - tp) * d >= 0:
                    close_trade(i, o[i], "TP_gap")
            if pos:
                hit_sl = (l[i] <= sl) if d == 1 else (h[i] >= sl)
                hit_tp = p.use_tp and ((h[i] >= tp) if d == 1 else (l[i] <= tp))
                if hit_sl:
                    close_trade(i, sl * (1 - slip * d), "SL")
                elif hit_tp:
                    close_trade(i, tp, "TP")

        # 4) bar-close logic: signals for next open
        if i >= warm and not np.isnan(slow[i]) and not np.isnan(slow[i - 1]):
            xu = fast[i] > slow[i] and fast[i - 1] <= slow[i - 1]
            xd = fast[i] < slow[i] and fast[i - 1] >= slow[i - 1]

            if pos:
                d = pos
                if (d == 1 and xd) or (d == -1 and xu):
                    pend_exit = True
                elif p.exit_mode != "none":
                    ref = slow if p.exit_mode == "price_slow" else fast
                    if d == 1 and c[i - 1] >= ref[i - 1] and c[i] < ref[i]:
                        pend_exit = True
                    elif d == -1 and c[i - 1] <= ref[i - 1] and c[i] > ref[i]:
                        pend_exit = True

            sig = 1 if xu else (-1 if xd else 0)
            if sig == 1 and not p.allow_long:
                sig = 0
            if sig == -1 and not p.allow_short:
                sig = 0
            if sig:
                ok = True
                if adx is not None and not (adx[i] >= p.adx_min):
                    ok = False
                if p.min_spread_pct > 0 and \
                        abs(fast[i] - slow[i]) / c[i] * 100 < p.min_spread_pct:
                    ok = False
                if ok and (pos == 0 or pos == -sig):
                    buf = p.sl_atr_buffer * (atr[i] if not np.isnan(atr[i]) else 0.0)
                    lo = max(0, i - p.swing_lookback + 1)
                    pend_sl = ((l[lo:i + 1].min() - buf) if sig == 1
                               else (h[lo:i + 1].max() + buf))
                    pend_entry = sig
                    if pos == -sig:
                        pend_exit = True  # flip

        # 5) mark-to-market
        eq_curve[i] = equity + (qty * (c[i] - entry) * pos if pos else 0.0)
        gross_curve[i] = qty * c[i] / equity if (pos and equity > 0) else 0.0

    if pos:
        close_trade(n - 1, c[-1], "eod")
        eq_curve[-1] = equity
        gross_curve[-1] = 0.0

    eq = pd.Series(eq_curve, index=idx, name="equity")
    tr = pd.DataFrame(trades)
    aux = {
        "funding_paid": float(funding_total),
        "fees_paid": float(fees_total),
        "avg_gross_leverage": float(np.nanmean(gross_curve)) if n else 0.0,
        "max_gross_leverage": float(np.nanmax(gross_curve)) if n else 0.0,
    }
    return tr, eq, aux


def metrics(trades: pd.DataFrame, eq: pd.Series, p: Params,
            aux: dict | None = None) -> dict:
    out: dict = {}
    aux = aux or {}
    dt = pd.Series(eq.index).diff().dt.total_seconds().median()
    bpy = 365 * 24 * 3600 / dt if dt and dt > 0 else np.nan
    r = eq.pct_change().dropna()
    years = (eq.index[-1] - eq.index[0]).total_seconds() / (365 * 24 * 3600)
    total = eq.iloc[-1] / p.initial_equity - 1
    dd = (eq / eq.cummax() - 1).min()
    out["bars"] = len(eq)
    out["return_pct"] = total * 100
    out["final_equity"] = float(eq.iloc[-1])
    out["cagr_pct"] = (((1 + total) ** (1 / years) - 1) * 100
                       if years > 0 and total > -1 else np.nan)
    out["sharpe"] = r.mean() / r.std() * np.sqrt(bpy) if r.std() > 0 else np.nan
    dn = r[r < 0].std()
    out["sortino"] = r.mean() / dn * np.sqrt(bpy) if dn and dn > 0 else np.nan
    out["max_dd_pct"] = dd * 100
    out["calmar"] = (out["cagr_pct"] / abs(out["max_dd_pct"])
                     if dd < 0 else np.nan)
    out["n_trades"] = len(trades)
    out["funding_paid"] = float(aux.get("funding_paid", 0.0))
    out["fees_paid"] = float(aux.get("fees_paid", 0.0))
    out["avg_gross_leverage"] = float(aux.get("avg_gross_leverage", 0.0))
    out["max_gross_leverage"] = float(aux.get("max_gross_leverage", 0.0))
    if len(trades):
        w = trades[trades.pnl > 0]
        ls = trades[trades.pnl <= 0]
        out["win_rate"] = len(w) / len(trades)
        out["profit_factor"] = (w.pnl.sum() / abs(ls.pnl.sum())
                                if len(ls) and ls.pnl.sum() != 0
                                else (float("inf") if len(w) else 0.0))
        out["gross_profit"] = float(w.pnl.sum())
        out["gross_loss"] = float(ls.pnl.sum())
        out["expectancy_R"] = float(trades.R.mean())
        out["avg_win_R"] = float(w.R.mean()) if len(w) else np.nan
        out["avg_loss_R"] = float(ls.R.mean()) if len(ls) else np.nan
        out["avg_bars"] = float(trades.bars.mean())
        out["long_trades"] = int((trades.side == "long").sum())
        out["short_trades"] = int((trades.side == "short").sum())
        out["long_pnl"] = float(trades[trades.side == "long"].pnl.sum())
        out["short_pnl"] = float(trades[trades.side == "short"].pnl.sum())
        out["flag"] = "OK" if len(trades) >= MIN_TRADE_FLAG else "INSUFFICIENT_SAMPLE"
    else:
        out["profit_factor"] = 0.0
        out["win_rate"] = 0.0
        out["flag"] = "INSUFFICIENT_SAMPLE"
    out["start"] = str(eq.index[0].date())
    out["end"] = str(eq.index[-1].date())
    out["fee_bps_per_side"] = p.fee_bps
    out["slip_bps_per_side"] = p.slip_bps
    out["slippage_bps_per_side"] = p.slip_bps
    out["cost_rt_bps"] = 2 * (p.fee_bps + p.slip_bps)
    out["cost_bp_roundtrip"] = 2 * (p.fee_bps + p.slip_bps)
    out["win_rate_pct"] = 100.0 * out.get("win_rate", 0.0)
    out["boot_draws"] = 4000
    out["boot_seed"] = 7
    return out


def tables(trades: pd.DataFrame, eq: pd.Series) -> list[dict]:
    out: list[dict] = []
    if len(trades):
        for reason, g in trades.groupby("reason"):
            out.append({"kind": "exit_reason", "id": str(reason),
                        "n": int(len(g)), "pnl": float(g.pnl.sum()),
                        "avg_R": float(g.R.mean()),
                        "funding": float(g.funding.sum())})
        for side, g in trades.groupby("side"):
            w = g[g.pnl > 0].pnl.sum()
            ls = abs(g[g.pnl <= 0].pnl.sum())
            out.append({"kind": "side", "id": str(side), "n": int(len(g)),
                        "pnl": float(g.pnl.sum()),
                        "pf": (float(w / ls) if ls > 0
                               else (float("inf") if w > 0 else 0.0))})
        tr = trades.copy()
        tr["year"] = pd.to_datetime(tr.exit_time, utc=True).dt.year
        for year, g in tr.groupby("year"):
            w = g[g.pnl > 0].pnl.sum()
            ls = abs(g[g.pnl <= 0].pnl.sum())
            out.append({"kind": "year", "id": str(int(year)), "n": int(len(g)),
                        "pnl": float(g.pnl.sum()),
                        "pf": (float(w / ls) if ls > 0
                               else (float("inf") if w > 0 else 0.0))})
    return out


def _boot_mean_ci(pnls: np.ndarray, draws: int = 4000, seed: int = 7,
                  max_elems: int = 2_000_000):
    """Bootstrap CI of the MEAN per-trade PnL (chunked).

    A 1m cell can close 75k trades; a (draws x n) matrix would allocate
    gigabytes, so draws are taken in chunks of ~2M elements. Declared as
    `boot_draws`/`boot_seed` in the artifact.
    """
    n = len(pnls)
    if n < 2:
        return 0.0, 0.0, 1.0
    rng = np.random.default_rng(seed)
    chunk = max(1, min(draws, max_elems // n))
    means = []
    done = 0
    while done < draws:
        k = min(chunk, draws - done)
        idx = rng.integers(0, n, size=(k, n))
        means.append(pnls[idx].mean(axis=1))
        done += k
    means = np.concatenate(means)
    return (float(np.percentile(means, 2.5)),
            float(np.percentile(means, 97.5)),
            float((means <= 0).mean()))


# --------------------------------------------------------------------------- #
# Adapter entry point
# --------------------------------------------------------------------------- #
def run_paths(paths, params: dict):
    p = params_from(params)
    kline = next(x for x in paths if not x.endswith("_funding.json"))
    fund_path = next((x for x in paths if x.endswith("_funding.json")), None)

    df = load_klines(kline)
    n0 = len(df)
    fund_stats = {"events": 0, "before_first": 0, "after_last": 0,
                  "multi_bar_events": 0, "last_bar_events": 0,
                  "bars_trimmed_head": 0, "bars_trimmed_tail": 0,
                  "max_gap_h": 0.0}
    rate_by_bar = np.zeros(len(df), dtype=float)
    if fund_path and p.funding:
        settle_ms, rate = load_funding(fund_path)
        open_ms = _index_to_ms(df.index)
        rate_by_bar, fund_stats = funding_by_bar(open_ms, settle_ms, rate)
        # HARD EDGE: the replayed window must be fully funded. Head: start at
        # the bar that CONTAINS the first settlement (house convention).
        # Tail: end at the bar that contains the last settlement, so no bar is
        # charged zero funding by omission in either direction.
        i0 = max(0, int(np.searchsorted(open_ms, int(settle_ms[0]),
                                        side="right")) - 1)
        open_ms2 = open_ms[i0:]
        j1 = max(0, int(np.searchsorted(open_ms2, int(settle_ms[-1]),
                                        side="right")) - 1)
        df = df.iloc[i0:i0 + j1 + 1]
        rate_by_bar = rate_by_bar[i0:i0 + j1 + 1]
        fund_stats["bars_trimmed_head"] = i0
        fund_stats["bars_trimmed_tail"] = n0 - (i0 + j1 + 1)
        gaps_h = np.diff(settle_ms.astype(np.float64)) / 3.6e6
        fund_stats["max_gap_h"] = float(gaps_h.max()) if len(gaps_h) else 0.0

    tr, eq, aux = run_backtest(df, p, rate_by_bar)
    m = metrics(tr, eq, p, aux)

    # Funding coverage: measured on the replayed window, not asserted.
    m["funding_model"] = ("charged@settlements" if fund_path and p.funding
                          else "not_charged")
    m["funding_events"] = fund_stats.get("events", 0)
    m["funding_events_before_window"] = fund_stats.get("before_first", 0)
    m["funding_events_after_window"] = fund_stats.get("after_last", 0)
    m["funding_multi_bar_events"] = fund_stats.get("multi_bar_events", 0)
    m["funding_last_bar_events"] = fund_stats.get("last_bar_events", 0)
    m["bars_trimmed_head_for_funding"] = fund_stats.get("bars_trimmed_head", 0)
    m["bars_trimmed_tail_for_funding"] = fund_stats.get("bars_trimmed_tail", 0)
    m["funding_max_gap_h"] = fund_stats.get("max_gap_h", 0.0)
    m["funding_covers_bars"] = bool(fund_path and p.funding)
    m["funding_coverage_frac"] = 1.0 if (fund_path and p.funding) else 0.0
    m["funding_tail_bars"] = 0

    # accounting identity, asserted (not published as a hope)
    pnl_sum = float(tr.pnl.sum()) if len(tr) else 0.0
    resid = float(eq.iloc[-1] - p.initial_equity - pnl_sum)
    m["pnl_identity_resid"] = resid
    scale = max(1.0, abs(float(eq.iloc[-1])))
    if abs(resid) > 1e-6 * scale:
        raise AssertionError(
            f"accounting identity broken: eq[-1]-INIT={eq.iloc[-1] - p.initial_equity:.6f} "
            f"sum(pnl)={pnl_sum:.6f} resid={resid:.6f}")

    # ---- institutional metrics measured INSIDE the artifact (bt.py battery) --
    e = eq.to_numpy(float)
    ns = len(e)
    thirds = []
    for k in range(3):
        a, b = int(ns * k / 3), int(ns * (k + 1) / 3)
        thirds.append(100.0 * (e[b - 1] / e[a] - 1.0)
                      if b > a and e[a] > 0 else 0.0)
    m["thirds_net_pct"] = [float(x) for x in thirds]
    m["n_periods_green"] = int(sum(1 for x in thirds if x > 0))
    halves = []
    for k in range(2):
        a, b = int(ns * k / 2), int(ns * (k + 1) / 2)
        halves.append(100.0 * (e[b - 1] / e[a] - 1.0)
                      if b > a and e[a] > 0 else 0.0)
    m["halves_net_pct"] = [float(x) for x in halves]
    m["n_halves_green"] = int(sum(1 for x in halves if x > 0))

    split = int(ns * 0.7)
    m["oos_split_bar"] = split
    m["oos_split_time"] = str(eq.index[min(split, ns - 1)])
    m["oos_return_pct"] = (100.0 * (e[-1] / e[split] - 1.0)
                           if ns > split + 1 and e[split] > 0 else 0.0)
    if len(tr):
        ent = pd.to_datetime(tr.entry_time, utc=True)
        oos_mask = (ent >= eq.index[min(split, ns - 1)]).to_numpy()
        pn_oos = tr.pnl.to_numpy(float)[oos_mask]
        gp = pn_oos[pn_oos > 0].sum()
        gl = -pn_oos[pn_oos < 0].sum()
        m["oos_n_trades"] = int(oos_mask.sum())
        m["oos_profit_factor"] = (float(gp / gl) if gl > 0
                                  else (float("inf") if gp > 0 else 0.0))
        pnls = tr.pnl.to_numpy(float)
        total = float(pnls.sum())
        top5 = float(np.sort(pnls)[::-1][:5].sum())
        m["conc_top5_pnl"] = top5
        m["conc_top5_share_pct"] = (100.0 * top5 / total
                                    if total != 0 else float("nan"))
        m["conc_net_without_top5_pct"] = (
            100.0 * (total - top5) / p.initial_equity)
        lo, hi, p0 = _boot_mean_ci(pnls)
        m["boot_ci_lo"] = lo
        m["boot_ci_hi"] = hi
        m["boot_p_le_zero"] = p0
    else:
        m["oos_n_trades"] = 0
        m["oos_profit_factor"] = 0.0
        m["conc_top5_pnl"] = 0.0
        m["conc_top5_share_pct"] = 0.0
        m["conc_net_without_top5_pct"] = 0.0
        m["boot_ci_lo"] = 0.0
        m["boot_ci_hi"] = 0.0
        m["boot_p_le_zero"] = 1.0

    # buy & hold on the SAME replayed window, zero costs, no leverage
    o0 = float(df["open"].iloc[0])
    c1 = float(df["close"].iloc[-1])
    m["buy_hold_return_pct"] = 100.0 * (c1 / o0 - 1.0) if o0 > 0 else 0.0

    # two controls measured inside the artifact: funding drag and zero cost
    if fund_path and p.funding:
        tr_nf, eq_nf, aux_nf = run_backtest(df, Params(**{**asdict(p), "funding": False}),
                                            np.zeros(len(df)))
        mnf = metrics(tr_nf, eq_nf, Params(**{**asdict(p), "funding": False}), aux_nf)
        m["no_funding_return_pct"] = mnf["return_pct"]
        m["no_funding_pf"] = mnf["profit_factor"]
        m["funding_drag_pp"] = m["return_pct"] - mnf["return_pct"]
    else:
        m["no_funding_return_pct"] = m["return_pct"]
        m["no_funding_pf"] = m["profit_factor"]
        m["funding_drag_pp"] = 0.0

    zc = Params(**{**asdict(p), "fee_bps": 0.0, "slip_bps": 0.0})
    trz, eqz, auxz = run_backtest(df, zc, rate_by_bar)
    mz = metrics(trz, eqz, zc, auxz)
    m["zero_cost_return_pct"] = mz["return_pct"]
    m["zero_cost_pf"] = mz["profit_factor"]
    m["zero_cost_n_trades"] = mz["n_trades"]

    prov = {"adapter": "ema921", "engine_version": "ema921-1",
            "source_of_record": "code/ema921_source.py",
            "source_sha256": "8be0020d057a4ef73fbed9e4ab4f11b97d131f3d62b3094f47e6ded80a2189c4"}
    return m, prov, tables(tr, eq)


if __name__ == "__main__":
    sys.exit("run through vrun.py")
