#!/usr/bin/env python
"""q10_engine.py -- the six surviving declared cells of the Qwen ten-card pack.

Cards implemented here (from results/qwen_pack10_grade.md, after Step zero):

  CARD1   funding-delta monthly rotation        long 2 lowest | short 2 highest,
                                                key = trailing 7d settled-funding
                                                delta; monthly, fill t+1, no stops.
  CARD2   low-vol monthly cross-section L/S     10 names; long 5 lowest 30d
                                                realized vol, short 5 highest.
  CARD3   turn-of-month BTC/ETH                 long basket from the day-27
                                                close decision: entry fill at the
                                                day-28 00:00 open, exit fill at
                                                the day-3 00:00 open; one unit per
                                                month.
  CARD4   funding-regime biweekly long/flat     panel funding index (equal-weight
                                                mean of the four majors' prints,
                                                BTC-anchored); gate = mean14 <=
                                                median365; long 0.25 per major
                                                while true, flat otherwise; |
                                                decision every 14 days.
  CARD9   vol term-structure long/flat          monthly; long the four majors at
                                                0.25 each iff 7d RV < 0.8 x 30d RV
                                                (std of 1h log returns, 168 vs 720
                                                trailing bars), flat otherwise.
  CARD10  volume-growth monthly L/S             10 names; long 5 lowest 30d/180d
                                                volume-growth, short 5 highest.

Cards five, six, seven, eight are NOT implemented: they were killed at Step
zero by their own pre-declared diagnostic bars (results/q10_step0.md) and no
alternates were declared.

Conventions, pinned before any run (carried from the grade file):

  * repo6x5 taker costs: 6 bps fee + 5 bps slippage = 11 bps PER FILL, on the
    leg's notional (leg weight x total gross 1.0). A ROLL is not a fill: a
    leg that keeps its side at a rebalance pays nothing; the join is recorded
    so closed units stay leg-decision-months with the price carried forward.
  * funding is billed ONLY on settled prints strictly after entry and
    strictly before exit, on the leg's notional, both directions. Cards two
    and ten have funding files for four of ten names only: those four are
    billed, the other six are NOT (no synthetic rates, C8); the declared
    cards assign zero funding budget, so the scored economics are unchanged
    by the missing files, and billable names are recorded in the artifact.
  * "gross 1x" = total gross of one: L/S buckets half left / half right at
    the declared leg weights.
  * closed units: cards one, two, ten = leg decision-months; cards four,
    nine = decision-period basket states (only in-market states are units);
    card three = month windows.
    PF, concentration and G6 are computed on unit-relative net P&L in bps of
    the unit's own notional; the share metrics weight units by their book
    weight.
  * G4 is read as: years fully inside the scored span, counted green on the
    linear equity curve; pass requires green >= ceil(2/3 x full years).
  * G5 benchmarks, per the pinned mapping (grade file F6): L/S books (one,
    two, ten) vs the equal-weight BUY-AND-HOLD of their universe over the
    same span; long/flat and window books (three, four, nine) vs their own
    basket B&H. Linear, no rebalancing, on both sides.
  * billed spans: monthly books score FULL months only (exit fill at the
    next month start's open); a book stranded after its last valid decision
    is liquidated at the final common bar open with a real 11 bps exit fee,
    flagged final_liquidation in the artifact.
  * determinism: no RNG anywhere; ranks break ties by symbol name; every
    loop iterates sorted keys.

Known-answer audit: code/_q10_audit.py must PASS before and after any change
to this file; the harness verify re-runs bit-for-bit (REGLA 0).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import q10_diag as D  # noqa: E402  (same loaders, same conventions)

FEE_SIDE = 0.0011          # repo6x5 per-side fill cost, fraction of notional
FEE_BPS = 11.0             # same, in bps of the leg's own notional
FUND_SYMS = D.FUND_SYMS    # BTC ETH SOL XRP
TEN_SYMS = D.TEN_SYMS
MS_DAY, MS_H, BP = D.MS_DAY, D.MS_H, D.BP
ENGINE_VERSION = "q10-engine-1"

EXPECTED_FILES = {
    "CARD1": sorted(f"{s}_1h.csv" for s in FUND_SYMS)
             + sorted(f"{s}_funding.json" for s in FUND_SYMS),
    "CARD2": sorted(f"{s}_1h.csv" for s in TEN_SYMS)
             + sorted(f"{s}_funding.json" for s in FUND_SYMS),
    "CARD3": sorted(f"{s}_1h.csv" for s in ("BTCUSDT", "ETHUSDT"))
             + sorted(f"{s}_funding.json" for s in ("BTCUSDT", "ETHUSDT")),
    "CARD4": sorted(f"{s}_1h.csv" for s in FUND_SYMS)
             + sorted(f"{s}_funding.json" for s in FUND_SYMS),
    "CARD9": sorted(f"{s}_1h.csv" for s in FUND_SYMS)
             + sorted(f"{s}_funding.json" for s in FUND_SYMS),
    "CARD10": sorted(f"{s}_1h.csv" for s in TEN_SYMS)
              + sorted(f"{s}_funding.json" for s in FUND_SYMS),
}


# ------------------------------------------------------------- loading utils
def _check_files(card: str, paths: list) -> dict:
    """Exact input-set enforcement: every engine input is hashed, none extra."""
    exp = sorted(EXPECTED_FILES[card])
    b = D._by_base(paths)
    got = sorted(b)
    if got != exp or len(paths) != len(exp):
        raise ValueError(f"{card}: input file set mismatch {got} != {exp}")
    return b


def _kline(path: str) -> dict:
    k = D._load_klines(path)
    k["lr"] = np.diff(np.log(k["c"]))          # 1h log returns (close-to-close)
    k["lc"] = np.log(k["c"])
    return k


def _rv(k: dict, i: int, n: int):
    """Std (ddof=1) of the n-bar trailing hourly log returns, ending strictly
    before close of bar i-1: exactly the step-zero slice lr[i-n : i-1]."""
    if i < n or (i - 1) > len(k["lr"]) - 1:
        return None
    return float(np.std(k["lr"][i - n:i - 1], ddof=1))


def _bar_idx(k: dict, t: int):
    """Index of the bar stamped exactly t, else None."""
    i = int(np.searchsorted(k["t"], t, side="left"))
    if i < len(k["t"]) and k["t"][i] == t:
        return i
    return None


def _c_at_or_before(k, t):
    """Close of the last bar with open_ts <= t (bar ownership by open ts)."""
    i = int(np.searchsorted(k["t"], t, side="right")) - 1
    return float(k["c"][i]) if i >= 0 else None


def _episode(sym: str, side: float, w: float, entry_ts: int, entry_px: float,
             in_fee_bps: float) -> dict:
    """One open leg (or one rolled leg-continuation)."""
    return {"sym": sym, "side": float(side), "w": float(w),
            "entry_ts": int(entry_ts), "entry_px": float(entry_px),
            "in_fee_bps": float(in_fee_bps),
            "exit_ts": None, "exit_px": None, "exit_fee_bps": None,
            "exit_reason": None,
            "funding_n": 0, "funding_bps": 0.0, "billable": False}


def _close(ep: dict, ts: int, px: float, fee_bps: float, reason: str):
    ep["exit_ts"] = int(ts)
    ep["exit_px"] = float(px)
    ep["exit_fee_bps"] = float(fee_bps)
    ep["exit_reason"] = reason
    return ep


# ------------------------------------------------------------------ executor
def _execute(events, kl):
    """Walk ordered fill events; emit closed leg episodes with real fees.

    events: [(fill_ts_ms, {sym: (side, w)})]. A leg absent from a decision's
    targets goes flat; a leg keeping its exact side AND weight ROLLS (no fee,
    episode split with the price carried forward). Every event's fill price
    is the open of the bar stamped at the event instant (must exist).
    """
    openlegs = {}
    episodes = []
    for ev in events:
        ts, targets = int(ev[0]), ev[1]
        reason = ev[2] if len(ev) > 2 and ev[2] else "rebalance"
        px = {}
        for sym in sorted(set(openlegs) | set(targets)):
            p = D._open_at(kl[sym], ts)
            if p is None:
                raise ValueError(f"no open price for {sym} at {ts}")
            px[sym] = p
        for sym in sorted(list(openlegs)):
            cur = openlegs[sym]
            tgt = targets.get(sym)
            if tgt is not None and (float(tgt[0]), float(tgt[1])) == \
               (cur["side"], cur["w"]):
                _close(cur, ts, px[sym], 0.0, "roll")
                episodes.append(cur)
                openlegs[sym] = _episode(sym, cur["side"], cur["w"], ts,
                                         px[sym], 0.0)
            else:
                _close(cur, ts, px[sym], FEE_BPS, reason)
                episodes.append(cur)
                del openlegs[sym]
        for sym in sorted(targets):
            if sym in openlegs:
                continue
            side, w = targets[sym]
            openlegs[sym] = _episode(sym, side, w, ts, px[sym], FEE_BPS)
    if openlegs:
        raise ValueError("book not fully closed: builder must end with a "
                         "final close event")
    return episodes


def _bill(episodes, funds):
    """Funding on settled prints strictly inside (entry_ts, exit_ts), bps of
    the leg's own notional, both directions: long pays r, short collects r."""
    for ep in episodes:
        vf = funds.get(ep["sym"])
        if vf is None:
            ep["funding_n"] = 0
            ep["funding_bps"] = 0.0
            continue
        ts_f, r_f = vf
        i0 = int(np.searchsorted(ts_f, ep["entry_ts"], side="right"))
        i1 = int(np.searchsorted(ts_f, ep["exit_ts"], side="left"))
        seg = r_f[i0:i1] if i1 > i0 else np.zeros(0)
        ep["funding_n"] = int(len(seg))
        ep["funding_bps"] = float((-ep["side"]) * float(seg.sum()) * BP)
        ep["billable"] = True


# -------------------------------------------------------------------- scorer
def _pf(vals) -> float:
    p = sum(v for v in vals if v > 0.0)
    n = -sum(v for v in vals if v < 0.0)
    if n > 0.0:
        return float(p / n)
    return float("inf") if p > 0.0 else 0.0


def _ceil23(n: int) -> int:
    return -(-2 * n // 3)


def _years(grid_t, cum, gs, ge):
    """Full calendar years inside the scored span: green iff the linear equity
    rose over the year. Returns (n_full, n_green, detail, by_year)."""
    full, green, det, byyr = 0, 0, [], {}
    ys = int(pd.Timestamp(int(grid_t[gs]), unit="ms", tz="UTC").year)
    ye = int(pd.Timestamp(int(grid_t[ge]), unit="ms", tz="UTC").year)
    for y in range(ys, ye + 1):
        a = int(pd.Timestamp(y, 1, 1, tz="UTC").timestamp() * 1000)
        b = int(pd.Timestamp(y + 1, 1, 1, tz="UTC").timestamp() * 1000)
        if a < grid_t[gs] or b - MS_H > grid_t[ge]:
            continue
        i0 = int(np.searchsorted(grid_t, a, side="left"))
        i1 = int(np.searchsorted(grid_t, b - MS_H, side="right")) - 1
        s0 = float(cum[i0 - 1]) if i0 > 0 else 0.0
        s1 = float(cum[i1])
        full += 1
        g = bool(s1 > s0)
        green += 1 if g else 0
        byyr[str(y)] = g
        det.append(f"{y}:{(s1 - s0) * 1e4:+.2f}")
    return full, green, "|".join(det), byyr


def _ep_net_bps(ep: dict) -> float:
    """Leg-relative net unit PnL, bps of the leg's own notional."""
    pnl = ep["side"] * (float(np.log(ep["exit_px"]))
                        - float(np.log(ep["entry_px"]))) * BP
    return float(pnl + ep["funding_bps"] - ep["in_fee_bps"]
                 - ep["exit_fee_bps"])


def _score_book(card, kl, funds, episodes, syms, card_extra=None,
                extra_rows=None):
    """Bill funding, build the linear equity on the common hourly grid,
    assemble closed units per the card's pinned unit definition, compute the
    G1-G6 gates, the G5 benchmark, and the tables. A parity check asserts the
    equity path sums to the unit path before anything is returned."""
    eps = [dict(e) for e in episodes]
    eps.sort(key=lambda e: (e["entry_ts"], e["sym"]))
    _bill(eps, funds)
    if funds and card in ("CARD2", "CARD10"):
        for s in syms:
            if funds.get(s) is None and s in FUND_SYMS:
                raise ValueError(f"{card}: missing funding file for {s}")

    # common hourly grid over the scored span
    t_start = min(e["entry_ts"] for e in eps)
    t_end = max(e["exit_ts"] for e in eps)
    n_h = (t_end - t_start) // MS_H + 1
    grid_t = t_start + np.arange(n_h, dtype=np.int64) * np.int64(MS_H)
    off, lc, o_arr = {}, {}, {}
    for s in syms:
        k = kl[s]
        i0 = int(np.searchsorted(k["t"], t_start, side="left"))
        if i0 == 0:
            raise ValueError(f"{card}: {s} has no pre-span bar for the bench")
        if k["t"][i0] != t_start or k["t"][i0 + n_h - 1] != t_end:
            raise ValueError(f"{card}: {s} kline grid misaligned with the "
                             f"scored span {t_start}..{t_end}")
        off[s] = i0
        lc[s] = k["lc"]
        o_arr[s] = k["o"]
        if not np.all(np.diff(k["t"][i0:i0 + n_h]) == MS_H):
            raise ValueError(f"{card}: {s} grid gap inside the span")

    contrib = np.zeros(n_h, dtype=float)
    for ep in eps:
        s, w, side = ep["sym"], ep["w"], ep["side"]
        e_g = (ep["entry_ts"] - t_start) // MS_H
        x_g = (ep["exit_ts"] - t_start) // MS_H
        if not (0 <= e_g < x_g <= n_h - 1):
            raise ValueError(f"{card}: episode {ep['entry_ts']}.."
                             f"{ep['exit_ts']} outside the scored span")
        contrib[e_g] += side * w * (lc[s][off[s] + e_g]
                                    - float(np.log(ep["entry_px"])))
        if x_g - e_g > 1:
            contrib[e_g + 1:x_g] += side * w * np.diff(
                lc[s][off[s] + e_g:off[s] + x_g])
        contrib[x_g] += side * w * (float(np.log(ep["exit_px"]))
                                    - lc[s][off[s] + x_g - 1])
        contrib[e_g] -= w * (ep["in_fee_bps"] / BP)
        contrib[x_g] -= w * (ep["exit_fee_bps"] / BP)
        if ep["funding_n"]:
            ts_f, r_f = funds[s]
            j0 = int(np.searchsorted(ts_f, ep["entry_ts"], side="right"))
            j1 = int(np.searchsorted(ts_f, ep["exit_ts"], side="left"))
            for pt, rr in zip(ts_f[j0:j1], r_f[j0:j1]):
                gi = (int(pt) - t_start) // MS_H
                if not (0 <= gi < n_h):
                    raise ValueError(f"{card}: funding print outside span")
                contrib[gi] += -side * w * float(rr)

    cum = np.cumsum(contrib)
    book_net_frac = float(cum[-1])

    # closed units per card semantics
    units = []
    if card in ("CARD1", "CARD2", "CARD10"):
        for ep in eps:
            units.append({"label": ep["sym"], "w": ep["w"],
                          "entry_ts": ep["entry_ts"], "exit_ts": ep["exit_ts"],
                          "pnl_bps": _ep_net_bps(ep),
                          "price_bps": ep["side"] * (float(np.log(ep["exit_px"]))
                                                     - float(np.log(ep["entry_px"]))) * BP,
                          "funding_bps": ep["funding_bps"],
                          "fee_bps": ep["in_fee_bps"] + ep["exit_fee_bps"],
                          "final": ep["exit_reason"] == "final_liquidation",
                          "legs": 1})
    else:
        groups = {}
        for ep in eps:
            groups.setdefault((ep["entry_ts"], ep["exit_ts"]), []).append(ep)
        for key in sorted(groups):
            grp = groups[key]
            net = sum(e["w"] * _ep_net_bps(e) for e in grp)
            units.append({
                "label": "+".join(sorted(e["sym"] for e in grp)), "w": 1.0,
                "entry_ts": key[0], "exit_ts": key[1], "pnl_bps": net,
                "price_bps": sum(e["w"] * e["side"]
                                 * (float(np.log(e["exit_px"]))
                                    - float(np.log(e["entry_px"]))) * BP
                                 for e in grp),
                "funding_bps": sum(e["w"] * e["funding_bps"] for e in grp),
                "fee_bps": sum(e["w"] * (e["in_fee_bps"] + e["exit_fee_bps"])
                               for e in grp),
                "final": any(e["exit_reason"] == "final_liquidation"
                             for e in grp),
                "legs": len(grp)})
    n_units = len(units)
    w_net = [u["w"] * u["pnl_bps"] for u in units]
    total_w = float(sum(w_net))
    parity_bps = abs(book_net_frac * 1e4 - total_w)
    if parity_bps > 1e-6:
        raise ValueError(f"{card}: equity/unit parity FAILED "
                         f"({parity_bps:.3e} bps)")

    price_total_bps = sum(u["w"] * u["price_bps"] for u in units)
    fund_total_bps = sum(u["w"] * u["funding_bps"] for u in units)
    fee_total_bps = sum(u["w"] * u["fee_bps"] for u in units)
    if abs(price_total_bps + fund_total_bps - fee_total_bps - total_w) > 1e-6:
        raise ValueError(f"{card}: unit decomposition mismatch")

    nf, ng, ydet, byyr = _years(grid_t, cum, 0, len(grid_t) - 1)
    eq = 1.0 + cum
    peak = np.maximum.accumulate(eq)
    mdd_pct = float(np.max((peak - eq) / peak) * 100.0)

    # G5 benchmark: equal-weight basket B&H over the same span, linear
    bench = np.zeros(n_h, dtype=float)
    for s in syms:
        bench += np.diff(lc[s][off[s] - 1:off[s] + n_h])
    bench /= float(len(syms))
    bench_frac = float(bench.sum())
    closed_form = sum(float(lc[s][off[s] + n_h - 1])
                      - float(lc[s][off[s] - 1]) for s in syms) / len(syms)
    if abs(bench_frac - closed_form) > 1e-8:
        raise ValueError(f"{card}: bench telescoping check failed")
    book_pct, bench_pct = 100.0 * book_net_frac, 100.0 * bench_frac

    units_pnl = [u["pnl_bps"] for u in units]
    pfb = _pf(units_pnl)
    pfz = _pf([u["pnl_bps"] - u["fee_bps"] for u in units])
    srt = sorted(w_net, reverse=True)
    top5_w = float(sum(srt[:5]))
    tshare = total_w if total_w != 0 else float("nan")
    best5_share_pct = 100.0 * top5_w / tshare if tshare == tshare \
        else float("nan")
    without_top5 = total_w - top5_w

    mid_ms = (t_start + t_end) // 2
    h1u = [u["pnl_bps"] for u in units if u["entry_ts"] < mid_ms]
    h2u = [u["pnl_bps"] for u in units if u["entry_ts"] >= mid_ms]
    pf_h1, pf_h2 = _pf(h1u), _pf(h2u)

    fills = sum(1 for e in eps if e["in_fee_bps"] > 0) + \
        sum(1 for e in eps if e["exit_fee_bps"] > 0)
    n_final = sum(1 for e in eps if e["exit_reason"] == "final_liquidation")

    gates = {
        "g1_pf_strict_gt_1p2": bool(pfb > 1.2),
        "g2_units_ge_30": bool(n_units >= 30),
        "g3_pf_gt_1_both_halves": bool(pf_h1 > 1.0 and pf_h2 > 1.0),
        "g4_green_years_ge_ceil_2of3": bool(nf >= 1 and ng >= _ceil23(nf)),
        "g5_beats_basket_bench": bool(book_pct > bench_pct),
        "g6_net_green_without_best5": bool(without_top5 > 0.0),
    }
    metrics = {
        "card": card,
        "units": n_units, "fills": fills, "final_liquidation_legs": n_final,
        "return_pct": book_pct, "buy_hold_bench_pct": bench_pct,
        "excess_vs_bench_pp": book_pct - bench_pct,
        "profit_factor": pfb, "profit_factor_zero_fee": pfz,
        "win_units_share_pct": 100.0 * sum(1 for p in units_pnl if p > 0)
                                     / n_units if n_units else float("nan"),
        "max_dd_pct": mdd_pct,
        "price_total_bps": price_total_bps,
        "funding_total_bps": fund_total_bps,
        "fee_total_bps": fee_total_bps,
        "net_total_bps_on_gross1x": total_w,
        "parity_units_vs_equity_bps": parity_bps,
        "n_full_years": nf, "n_green_years": ng, "g4_required_green": _ceil23(nf),
        "year_net_bps": ydet,
        "g3_half1_pf": pf_h1, "g3_half2_pf": pf_h2,
        "best5_share_pct": best5_share_pct, "net_without_best5_bps": without_top5,
        "span_first": t_start, "span_last": t_end,
        "span_days": (t_end - t_start) / MS_DAY,
        "gates_pass_all": bool(all(gates.values())),
        "gates_pass_count": int(sum(1 for v in gates.values() if v)),
    }
    metrics.update({k: bool(v) for k, v in gates.items()})
    if card_extra:
        metrics.update(card_extra)

    tables = []
    for u in units:
        tables.append({"kind": "unit", "card": card, "sym": u["label"],
                       "legs": u["legs"], "w": u["w"],
                       "entry_ts": u["entry_ts"], "exit_ts": u["exit_ts"],
                       "pnl_bps": u["pnl_bps"], "price_bps": u["price_bps"],
                       "funding_bps": u["funding_bps"], "fee_bps": u["fee_bps"],
                       "final_close": u["final"]})
    for r in (extra_rows or []):
        tables.append(r)
    return metrics, eps, tables


# --------------------------------------------------------------- card building
def _midnight_open(kl, syms, t):
    """True when every symbol has a tradable open bar at t."""
    return all(D._open_at(kl[s], t) is not None for s in syms)


def _trailing_close(events, last_scored, hi):
    """Monthly books: close the last full month's legs at the next month
    start's open when it exists inside the data; the final liquidation event
    always ends the book (a no-op when already flat)."""
    if last_scored is not None:
        m1 = D._next_month_ms(last_scored)
        if m1 <= hi:
            events.append((int(m1), {}, "month_close"))
    events.append((int(hi), {}, "final_liquidation"))
    return events


def _card1_build(kl, fund):
    """CARD1 buckets: long the two lowest | short the two highest trailing 7d
    settled-funding deltas (lagged: prints strictly before the decision
    instant), 0.25 per leg, monthly decision at each month start; a month
    with an under-covered 7d window holds the prior buckets (no event)."""
    lo = max(int(kl[s]["t"][0]) for s in FUND_SYMS)
    hi = min(int(kl[s]["t"][-1]) for s in FUND_SYMS)
    events, skipped, last = [], [], None
    for m0 in D._month_starts(lo, hi):
        if D._next_month_ms(m0) > hi:
            break
        d7 = None
        for s in FUND_SYMS:
            d = D._d7(fund[s][0], fund[s][1], m0)
            if d is None:
                d7 = None
                break
            d7 = d7 or {}
            d7[s] = d
        if d7 is None or not _midnight_open(kl, FUND_SYMS, m0):
            skipped.append(int(m0))
            continue
        order = sorted(FUND_SYMS, key=lambda s: (d7[s], s))
        targets = {order[0]: (1.0, 0.25), order[1]: (1.0, 0.25),
                   order[2]: (-1.0, 0.25), order[3]: (-1.0, 0.25)}
        events.append((int(m0), targets, "rebalance"))
        last = int(m0)
    return _trailing_close(events, last, hi)


def _rank_month_build(kl, key_fn, floor, w_leg):
    """Shared monthly L/S builder for cards 2 and 10: pick long/short buckets
    on the declared key at each month start, 0.1 per leg, ten names; a month
    with an under-covered history holds the prior buckets (no event)."""
    syms = sorted(kl)
    lo = max(int(kl[s]["t"][0]) for s in syms)
    hi = min(int(kl[s]["t"][-1]) for s in syms)
    events, skipped, decisions, last = [], [], [], None
    for m0 in D._month_starts(lo, hi):
        if D._next_month_ms(m0) > hi:
            break
        key, ok = {}, True
        for s in syms:
            i = _bar_idx(kl[s], m0)
            if i is None or i < floor:
                ok = False
                break
            key[s] = key_fn(kl[s], i)
            if key[s] is None or not np.isfinite(key[s]):
                ok = False
                break
        if not ok or not _midnight_open(kl, syms, m0):
            skipped.append(int(m0))
            continue
        decisions.append({"ts": int(m0), "key": dict(key)})
        order = sorted(syms, key=lambda s: (key[s], s))
        targets = {s: (1.0, w_leg) for s in order[:5]}
        targets.update({s: (-1.0, w_leg) for s in order[5:]})
        events.append((int(m0), targets, "rebalance"))
        last = int(m0)
    return _trailing_close(events, last, hi)


def _card2_build(kl):
    """CARD2: long the 5 lowest 30d realized vols, short the 5 highest."""
    return _rank_month_build(
        kl, lambda k, i: _rv(k, i, 720), 720, 0.1)


def _card10_build(kl):
    """CARD10: long the 5 lowest 30d/180d volume-growth keys, short the 5
    highest (mean volume trailing 720 bars / mean volume trailing 4320)."""

    def _growth(k, i):
        v720 = float(np.mean(k["v"][i - 720:i - 1]))
        v180 = float(np.mean(k["v"][i - 4320:i - 1]))
        return v720 / v180 if v180 > 0 else None

    return _rank_month_build(kl, _growth, 4320, 0.1)


def _card3_build(kl):
    """CARD3: one long BTC/ETH window per month; decision = the last close
    strictly before the previous month's day-28 00:00, entry fill at that
    open, exit fill at this month's day-3 00:00 open (real fills, both fee'd)."""
    syms3 = ("BTCUSDT", "ETHUSDT")
    lo = max(int(kl[s]["t"][0]) for s in syms3)
    hi = min(int(kl[s]["t"][-1]) for s in syms3)
    eps, skipped = [], []
    for m0 in D._month_starts(lo, hi):
        d28 = D._prev_month_start(m0) + 27 * MS_DAY
        d3 = m0 + 2 * MS_DAY
        if d3 > hi:
            continue
        legs, ok = [], True
        for s in syms3:
            c_dec = D._c_before(kl[s], d28)
            o_in = D._open_at(kl[s], d28)
            o_out = D._open_at(kl[s], d3)
            if c_dec is None or o_in is None or o_out is None \
               or o_in <= 0 or o_out <= 0:
                ok = False
                break
            legs.append(_episode(s, 1.0, 0.5, d28, o_in, FEE_BPS))
        if not ok:
            skipped.append(int(m0))
            continue
        for ep in legs:
            _close(ep, d3, D._open_at(kl[ep["sym"]], d3), FEE_BPS, "window")
        eps.extend(legs)
    return eps, len(skipped)


def _card49_build(kl, decision_ts, key_fn):
    """Shared long/flat builder for cards 4 (biweekly panel gate) and 9
    (monthly panel vol term-structure gate). decision_ts: the pre-declared
    decision instants; key_fn(ts) -> True/False/None (None = under-covered
    decision: hold the prior state, no book action)."""
    decisions = []
    for t in decision_ts:
        decisions.append({"ts": int(t), "gate": key_fn(int(t))})
    hi = min(int(kl[s]["t"][-1]) for s in FUND_SYMS)
    events, missing = [], 0
    for d in decisions:
        if d["gate"] is None:
            continue
        if not _midnight_open(kl, FUND_SYMS, d["ts"]):
            missing += 1
            continue
        targets = {s: (1.0, 0.25) for s in FUND_SYMS} if d["gate"] else {}
        events.append((d["ts"], targets, "rebalance"))
    events.append((hi, {}, "final_liquidation"))
    n_valid = sum(1 for d in decisions if d["gate"] is not None)
    n_true = sum(1 for d in decisions if d["gate"] is True)
    return events, decisions, n_valid, n_true, missing


def _prov(card, fund_syms):
    flag = {"CARD3": ("BTCUSDT", "ETHUSDT")}.get(card, tuple(FUND_SYMS))
    p = {"adapter": "q10", "engine_version": ENGINE_VERSION, "card": card,
         "costs": {"model": "repo6x5", "fee_bps": 6.0, "slippage_bps": 5.0,
                   "per_side_taker_bps": 11.0,
                   "maker_fills": "none (directional cards may not assume maker)",
                   "roll_is_not_a_fill": True},
         "conventions": {
             "fills": "entry/exit at the decision instant's 1h bar open; "
                      "side/weight-preserving rebalances are rolls (zero fee)",
             "gross1x": "total gross of one; leg weights per card",
             "funding_window": "settled prints strictly after entry and "
                               "strictly before exit, both directions, bps "
                               "of the leg's own notional",
             "equity": "linear on the common hourly bar grid; no compounding",
             "units": {"CARD1": "leg decision-months",
                       "CARD2": "leg decision-months",
                       "CARD10": "leg decision-months",
                       "CARD3": "month windows (2 legs)",
                       "CARD4": "decision-period basket states (in-market "
                                "only)",
                       "CARD9": "decision-period basket states (in-market "
                                "only)"}[card],
             "g4": "green years >= ceil(2/3 x full years), full years only",
             "g5": {"CARD1": "majors equal-weight basket B&H, linear",
                    "CARD2": "ten-name equal-weight basket B&H, linear",
                    "CARD10": "ten-name equal-weight basket B&H, linear",
                    "CARD3": "BTC/ETH basket B&H over the scored span, linear",
                    "CARD4": "majors basket B&H over the scored span, linear",
                    "CARD9": "majors basket B&H over the scored span, linear"
                    }.get(card, ""),
             "undecidable_months": "a decision whose declared data is absent "
                                   "or under-covered holds the prior state "
                                   "(no event, no synthetic rate, C8)",
         },
         "funding_billing": {
             "billed": sorted(fund_syms),
             "unbilled": sorted(set(syms) - set(fund_syms)) if
             (syms := (TEN_SYMS if card in ("CARD2", "CARD10")
                       else list(flag))) else [],
             "note": "cards 2/10 have no funding files for six of ten names; "
                     "those legs carry zero declared funding budget (C8), "
                     "the missing rate is never synthesized"},
         }
    return p


def run(card: str, paths: list):
    """Dispatch one declared q10 cell; returns (metrics, prov, tables)."""
    b = _check_files(card, paths)
    syms = (["BTCUSDT", "ETHUSDT"] if card == "CARD3"
            else (list(FUND_SYMS) if card in ("CARD1", "CARD4", "CARD9")
                  else list(TEN_SYMS)))
    kl = {s: _kline(b[f"{s}_1h.csv"]) for s in syms}
    if card == "CARD3":
        fund_syms_used = ["BTCUSDT", "ETHUSDT"]
    elif card in ("CARD1", "CARD4", "CARD9", "CARD2", "CARD10"):
        fund_syms_used = list(FUND_SYMS)
    else:
        raise ValueError(f"unknown q10 card: {card!r}")
    funds = {s: D._load_funding(b[f"{s}_funding.json"])
             for s in fund_syms_used}
    for s, k in kl.items():
        d = np.diff(k["t"])
        if d.size and int((d != MS_H).sum()) != 0:
            raise ValueError(f"{card}: {s} kline grid is not gapless hourly")

    period_check = {}
    for s in fund_syms_used:
        ts_f = funds[s][0]
        days = (ts_f[-1] - ts_f[0]) / MS_DAY
        period_check[f"fund_prints_per_day_{s}"] = float(len(ts_f) / (days + 1))

    if card == "CARD1":
        events = _card1_build(kl, funds)
        eps = _execute(events, kl)
        extra = {"universe": "BTC ETH SOL XRP; all four billed",
                 "n_scored_months": sum(1 for e in events
                                        if e[2] == "rebalance")}
        metrics, _, tables = _score_book(card, kl, funds, eps, syms, extra)
    elif card in ("CARD2", "CARD10"):
        events = _card2_build(kl) if card == "CARD2" else _card10_build(kl)
        eps = _execute(events, kl)
        extra = {"universe": "ten plain-history names; funding billed on the "
                             "four majors only (no files for the other six, "
                             "C8)",
                 "n_scored_months": sum(1 for e in events
                                        if e[2] == "rebalance"),
                 **period_check}
        metrics, _, tables = _score_book(card, kl, funds, eps, syms, extra)
    elif card == "CARD3":
        eps, n_skipped = _card3_build(kl)
        extra = {"universe": "BTC/ETH basket; one window per month",
                 "n_skipped_months": n_skipped, **period_check}
        metrics, _, tables = _score_book(card, kl, funds, eps, syms, extra)
    elif card in ("CARD4", "CARD9"):
        if card == "CARD4":
            p_ts, p_r, full_share = D._panel_funding(funds)
            t0 = (int(p_ts[0]) // MS_DAY) * MS_DAY
            dec_ts = []
            while t0 + 14 * MS_DAY <= int(p_ts[-1]):
                dec_ts.append(int(t0))
                t0 += 14 * MS_DAY

            def _key(t):
                st14 = D._fstats(p_ts, p_r, t, 14)
                st365 = D._fstats(p_ts, p_r, t, 365)
                if st14 is None or st365 is None \
                   or st14[0] < D.MIN_14D or st365[0] < D.MIN_365D:
                    return None
                return bool(st14[1] <= st365[2])
        else:
            lo = max(int(kl[s]["t"][0]) for s in FUND_SYMS)
            hi = min(int(kl[s]["t"][-1]) for s in FUND_SYMS)
            dec_ts = [int(m) for m in D._month_starts(lo, hi)]

            def _key(t):
                idx = {s: _bar_idx(kl[s], t) for s in FUND_SYMS}
                if any(v is None or v < 720 for v in idx.values()):
                    return None
                rv7s = [_rv(kl[s], idx[s], 168) for s in FUND_SYMS]
                rv30s = [_rv(kl[s], idx[s], 720) for s in FUND_SYMS]
                if any(v is None for v in rv7s + rv30s):
                    return None
                return bool(float(np.mean(rv7s)) < 0.8 * float(np.mean(rv30s)))
        events, decisions, n_valid, n_true, missing = _card49_build(
            kl, dec_ts, _key)
        eps = _execute(events, kl)
        extra = {"decisions_total": len(decisions),
                 "decisions_valid": n_valid,
                 "decisions_gate_true": n_true,
                 "in_market_decisions_pct":
                     100.0 * n_true / max(1, n_valid),
                 "decisions_no_open": missing,
                 "universe": "four majors at 0.25 each while the gate holds",
                 **period_check}
        if card == "CARD4":
            extra["panel_index_full_coverage_share"] = full_share
        metrics, _, tables = _score_book(card, kl, funds, eps, syms, extra)
    else:
        raise ValueError(f"unknown q10 card: {card!r}")
    return metrics, _prov(card, fund_syms_used), tables
