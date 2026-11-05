#!/usr/bin/env python3
"""
bookreplay_engine.py — fill-resolution replay: the SAME resting-maker grid
resolved two ways on the SAME window and levels, so the ONLY difference is
fill resolution:

  MODEL TRADES : fills resolved on REAL executed aggTrades (official Binance
                 bulk archive, data.binance.vision — hashed into the artifact).
                 A resting BUY at level L fills the moment a trade prints at
                 price <= L (a taker sell crossed our bid level — no cancel
                 ambiguity: these are actual executions). A resting SELL at
                 level H fills when a trade prints at price >= H. This is the
                 ground-truth maker-fill record at trade resolution.
  MODEL 15M    : the same levels resolved on 15m OHLC bars with the repo's
                 bar convention — a bid rung fills when bar.low <= L, a cover
                 when bar.high >= cover, and a same-bar entry+cover is CREDITED
                 (the optimistic convention the XRP neutral 15m engine uses and
                 the 1m-resolution audit identified as the same-bar-cover
                 inflation).

This measures the bar-convention overfill against REAL executions on REAL
forward data — the forward record the repo fill-model rule demands for
maker/intra-bar strategies. (Top-of-book bookTicker alone was tried first and
rejected for this purpose: it cannot distinguish a cancel from a trade in
either direction; only the trade stream can. See results/recorder_replay_*.json
for the tape-quality audit that motivated this.)

Declared simplifications (also carried in prov):
  - grid anchored ONCE at the first trade price; levels anchor*(1 -/+ k*spacing);
    no re-anchoring (both models share the exact same levels);
  - long covers at level*(1+spacing), short covers at level*(1-spacing)
    (classic grid rungs); one position per rung per arm at a time;
  - fill price IS the level (maker limit semantics), maker fee on every fill;
  - funding EXCLUDED from both models — the comparison isolates resolution;
  - trade transact_time is the replay clock; no queue-position modeling
    (a fill requires a trade through the level);
  - positions open at window end are marked at the last trade price and
    reported unrealized; the equity curves mark realized pnl at the cover bar.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SYMBOL_DEFAULT = "XRPUSDT"


def _load_trades(paths, symbol):
    """Load the REAL aggTrades CSVs for the window (data/aggtrades/<SYM>/),
    asserting day contiguity: a missing day in the middle would silently change
    which trades exist. Returns (ts_ms, price) sorted by ts, plus the day list."""
    files = []
    for p in paths:
        p = str(p)
        if p.lower().endswith(".csv") and "aggtrades" in p.lower():
            files.append(Path(p))
    if not files:
        raise RuntimeError(f"no aggTrades CSVs among inputs for {symbol}")
    files.sort(key=lambda f: f.name)          # name carries the date
    days = [f.stem.split("-aggTrades-")[-1] for f in files]
    expected = pd.date_range(days[0], days[-1], freq="D").strftime("%Y-%m-%d").tolist()
    missing = [d for d in expected if d not in days]
    if missing:
        raise RuntimeError(f"aggTrades window has missing days: {missing} — fetch them "
                           f"with code/fetch_aggtrades.py before running")
    ts_all, px_all = [], []
    for f in files:
        df = pd.read_csv(f, usecols=["price", "transact_time"])
        ts_all.append(df["transact_time"].to_numpy())
        px_all.append(df["price"].to_numpy(dtype="float64"))
    ts = np.concatenate(ts_all)
    px = np.concatenate(px_all)
    order = np.argsort(ts, kind="stable")
    return ts[order], px[order], days


def _walk_rung(entry_cross: np.ndarray, cover_cross: np.ndarray, same_ok: bool = False):
    """Alternating walk over precomputed crossing indices: entry, then the next
    cover after it, then re-entry, etc. Returns [(entry_idx, cover_idx|None)].

    same_ok=False (trade resolution): the cover search starts at entry+1 — a
    single execution can never be both the entry and the cover of one rung.
    same_ok=True (15m bar convention): the cover may land on the SAME bar as
    the entry (c == e), which is exactly the optimistic repo convention this
    probe measures — the XRP 1m audit showed the 15m engine credits a cover
    whenever the same bar's high reaches the cover level."""
    pairs = []
    cur = 0
    start = 0 if same_ok else 1
    while True:
        e_pos = int(np.searchsorted(entry_cross, cur, side="left"))
        if e_pos >= len(entry_cross):
            break
        e = int(entry_cross[e_pos])
        c_pos = int(np.searchsorted(cover_cross, e + start, side="left"))
        if c_pos >= len(cover_cross):
            pairs.append((e, None))          # still open at window end
            break
        c = int(cover_cross[c_pos])
        pairs.append((e, c))
        cur = c + 1
    return pairs


def run(in_paths, params):
    p = {
        "levels": 5, "spacing_pct": 0.3, "notional_usdt": 25.0,
        "equity0": 25.0, "maker_fee_bps": 2.0, "leverage_cap": 10.0,
    }
    p.update(params or {})
    symbol = p.get("symbol", SYMBOL_DEFAULT)

    csvs = [x for x in in_paths
            if str(x).lower().endswith(".csv") and "aggtrades" not in str(x).lower()]
    if not csvs:
        raise RuntimeError("bookreplay needs the 15m klines CSV among its inputs")
    bars = pd.read_csv(csvs[0])
    bars.columns = [c.strip().lower() for c in bars.columns]

    ts, px, trade_days = _load_trades(in_paths, symbol)
    t0, t1 = int(ts[0]), int(ts[-1])
    mid0 = float(px[0])

    # the trade window bounds BOTH models: the 15m model must not fill on days
    # outside it (same tradable window, only resolution differs)
    mask = (bars["open_ts"] >= t0) & (bars["open_ts"] <= t1)
    bars = bars.loc[mask].reset_index(drop=True)
    if bars.empty:
        raise RuntimeError("no 15m bars inside the trade window")

    spacing = p["spacing_pct"] / 100.0
    fee = p["maker_fee_bps"] / 10000.0
    notional = float(p["notional_usdt"])
    equity0 = float(p["equity0"])

    buy_levels = [mid0 * (1 - k * spacing) for k in range(1, p["levels"] + 1)]
    sell_levels = [mid0 * (1 + k * spacing) for k in range(1, p["levels"] + 1)]
    bar_close = bars["close"].to_numpy()
    bar_hi = bars["high"].to_numpy()
    bar_lo = bars["low"].to_numpy()
    bar_t0 = bars["open_ts"].to_numpy()
    n_bars = len(bars)

    def bar_of(ms):
        return int(np.searchsorted(bar_t0, ms, side="right")) - 1

    # ── MODEL TRADES (real executions) ─────────────────────────────────────
    # fills: (entry_bar, cover_bar_or_None, pnl_or_None); fees accrue per fill:
    # entry fee always, cover fee on cover.
    fee_tape = [0.0]

    def trade_arm(level, side):
        if side == "long":
            lc = level * (1 + spacing)
            pairs = _walk_rung(np.flatnonzero(px <= level), np.flatnonzero(px >= lc))
        else:
            hc = level * (1 - spacing)
            pairs = _walk_rung(np.flatnonzero(px >= level), np.flatnonzero(px <= hc))
        out = []
        for e, c in pairs:
            qty = notional / level
            ef = fee * notional
            fee_tape[0] += ef
            if c is None:
                out.append((bar_of(int(ts[e])), None, None))
                continue
            cf = fee * qty * (lc if side == "long" else hc)
            fee_tape[0] += cf
            pnl = (qty * (lc - level) - ef - cf if side == "long"
                   else qty * (level - hc) - ef - cf)
            out.append((bar_of(int(ts[e])), bar_of(int(ts[c])), pnl))
        return out

    tape_fills = []
    for L in buy_levels:
        tape_fills += trade_arm(L, "long")
    for H in sell_levels:
        tape_fills += trade_arm(H, "short")

    # ── MODEL 15M (same levels, bar convention, same-bar covers CREDITED) ──
    fee_bar = [0.0]

    def bar_arm(level, side):
        if side == "long":
            lc = level * (1 + spacing)
            pairs = _walk_rung(np.flatnonzero(bar_lo <= level),
                               np.flatnonzero(bar_hi >= lc), same_ok=True)
        else:
            hc = level * (1 - spacing)
            pairs = _walk_rung(np.flatnonzero(bar_hi >= level),
                               np.flatnonzero(bar_lo <= hc), same_ok=True)
        out = []
        for e, c in pairs:
            qty = notional / level
            ef = fee * notional
            fee_bar[0] += ef
            if c is None:
                out.append((int(e), None, None))
                continue
            cf = fee * qty * (lc if side == "long" else hc)
            fee_bar[0] += cf
            pnl = (qty * (lc - level) - ef - cf if side == "long"
                   else qty * (level - hc) - ef - cf)
            out.append((int(e), int(c), pnl))
        return out

    bar_fills = []
    for L in buy_levels:
        bar_fills += bar_arm(L, "long")
    for H in sell_levels:
        bar_fills += bar_arm(H, "short")
    same_bar_rt = sum(1 for e, c, _ in bar_fills if c is not None and c == e)

    def summarize(fills, label):
        closed = [(cb, pnl) for _, cb, pnl in fills if pnl is not None]
        open_end = sum(1 for _, c, _ in fills if c is None)
        wins = sum(1 for _, x in closed if x > 0)
        losses = sum(1 for _, x in closed if x <= 0)
        gross_win = sum(x for _, x in closed if x > 0)
        gross_loss = -sum(x for _, x in closed if x < 0)
        realized = sum(x for _, x in closed)
        eq = np.full(n_bars, equity0)
        acc = equity0
        k = 0
        cov = sorted((cb, pnl) for cb, pnl in closed)
        for i in range(n_bars):
            while k < len(cov) and cov[k][0] <= i:
                acc += cov[k][1]
                k += 1
            eq[i] = acc
        peak = np.maximum.accumulate(eq)
        dd = (peak - eq) / np.maximum(peak, 1e-12) * 100.0
        return {
            "model": label,
            "n_entries": len(fills),
            "n_closed": len(closed),
            "n_losses": int(losses),
            "n_open_end": open_end,
            "win_rate_pct": round(100.0 * wins / len(closed), 2) if closed else None,
            "profit_factor": (round(gross_win / gross_loss, 4)
                              if gross_loss > 1e-12 else None),
            "realized_pnl_usdt": round(realized, 4),
            "return_pct": round(100.0 * realized / equity0, 4),
            "max_dd_pct": round(float(dd.max()), 4),
        }, eq, realized

    tape_sum, tape_eq, tape_realized = summarize(tape_fills, "trades")
    bar_sum, bar_eq, bar_realized = summarize(bar_fills, "15m")

    # unrealized at window end, marked at the last trade price / last bar close
    def unrealized(levels, side, mark):
        u = 0.0
        for L in levels:
            if side == "long":
                pairs = _walk_rung(np.flatnonzero(px <= L),
                                   np.flatnonzero(px >= L * (1 + spacing)))
            else:
                pairs = _walk_rung(np.flatnonzero(px >= L),
                                   np.flatnonzero(px <= L * (1 - spacing)))
            for e, c in pairs:
                if c is None:
                    u += (notional / L) * (mark - L) if side == "long" \
                        else (notional / L) * (L - mark)
        return u

    last_px = float(px[-1])
    u_tape = (unrealized(buy_levels, "long", last_px)
              + unrealized(sell_levels, "short", last_px))
    u_bar = (unrealized(buy_levels, "long", float(bar_close[-1]))
             + unrealized(sell_levels, "short", float(bar_close[-1])))

    # margin / leverage sanity on the realized curve (gross at full capacity)
    max_gross = 2 * p["levels"] * notional
    lev_curve = max_gross / np.maximum(tape_eq, 1e-12)
    maint = 0.005 * max_gross
    buffer_pct = (tape_eq - maint) / np.maximum(tape_eq, 1e-12) * 100.0

    n_rt_b = bar_sum["n_closed"]
    metrics = {
        "window_days": round((t1 - t0) / 86400000.0, 3),
        "trade_days": len(trade_days),
        "trades": int(len(ts)),
        "bars": int(n_bars),
        "anchor_price": round(float(mid0), 8),
        "levels_per_side": int(p["levels"]),
        "spacing_pct": float(p["spacing_pct"]),
        "notional_usdt": notional,
        "maker_fee_bps": float(p["maker_fee_bps"]),
        "n_trades": int(tape_sum["n_closed"]),
        "return_pct": tape_sum["return_pct"],
        "profit_factor": tape_sum["profit_factor"],
        "win_rate": tape_sum["win_rate_pct"],
        "max_dd_pct": tape_sum["max_dd_pct"],
        "fees_trades_usdt": round(fee_tape[0], 4),
        "fees_15m_usdt": round(fee_bar[0], 4),
        "fills_trades": int(tape_sum["n_entries"]),
        "fills_15m": int(bar_sum["n_entries"]),
        "same_bar_rt_15m": int(same_bar_rt),
        "same_bar_rt_share_pct": (round(100.0 * same_bar_rt / n_rt_b, 2)
                                  if n_rt_b else None),
        "net_return_pct_trades": tape_sum["return_pct"],
        "net_return_pct_15m": bar_sum["return_pct"],
        "fill_inflation_pp": round(bar_sum["return_pct"] - tape_sum["return_pct"], 4),
        "realized_trades_usdt": round(tape_realized, 4),
        "realized_15m_usdt": round(bar_realized, 4),
        "unrealized_trades_usdt": round(u_tape, 4),
        "unrealized_15m_usdt": round(u_bar, 4),
        "open_end_trades": int(tape_sum["n_open_end"]),
        "open_end_15m": int(bar_sum["n_open_end"]),
        "min_margin_buffer_pct": round(float(buffer_pct.min()), 2),
        "max_gross_leverage": round(float(lev_curve.max()), 2),
        "bars_over_leverage": int((lev_curve > p["leverage_cap"]).sum()),
        "funding_charged": False,
    }
    prov = {
        "engine_version": "bookreplay-1",
        "fill_model": "maker_trade_prints (real aggTrades) vs maker_intrabar (15m bar convention)",
        "symbol": symbol,
        "trade_days": trade_days,
        "window_start_utc": str(pd.to_datetime(t0, unit="ms", utc=True)),
        "window_end_utc": str(pd.to_datetime(t1, unit="ms", utc=True)),
        "declared_simplifications": [
            "both models trade the same window bounded by the aggTrades files (contiguity asserted), so coverage cannot drive the difference",
            "grid anchored once at the first trade price; no re-anchoring; identical levels in both models",
            "touch semantics at each model's resolution: trades = a real execution prints at/beyond the level (no cancel ambiguity); 15m = bar.low<=L / bar.high>=H with same-bar covers CREDITED (the optimistic repo bar convention)",
            "fill price is the level; maker fee on every fill; funding excluded from both models so the comparison isolates fill resolution",
            "transact_time is the replay clock; no queue-position modeling; a fill requires a trade through the level",
            "open positions marked at the last trade price and reported unrealized; equity curves mark realized pnl at the cover bar only",
        ],
    }
    tables = [tape_sum, bar_sum]
    return metrics, prov, tables


if __name__ == "__main__":
    print("bookreplay_engine: run through code/vrun.py run --strategy bookreplay", file=sys.stderr)
