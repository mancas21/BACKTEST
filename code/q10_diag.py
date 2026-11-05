#!/usr/bin/env python
"""q10_diag.py -- Step-zero descriptive diagnostics for the registered Qwen
ten-card pack (results/qwen_pack10_grade.md).

NO trading, NO costs, NO strategy returns: pure descriptive measurement over
the raw funding JSONs and the plain 1h klines, with the pre-declared kill
bars from the grade file carried as honest boolean metrics.

One file, three modes, dispatched on params['mode']:

  funding   cards 1, 4, 5, 8: monthly realized funding-cash collection plus
            the long-minus-short PRICE differential for two bucket keys (the
            7d funding-delta key of card one, the 30d-avg-funding LEVEL key
            of card five), rank staleness of the delta key, the per-month
            settlement-hour episodes of card eight under the pinned F1
            convention, and the biweekly panel regime gate of card four
            (in-market fraction and spell persistence).

  calendar  cards 3, 6, 7: per-episode means of the turn-of-month window
            (close day-27 to close day-2, PLUS the fill-t+1 variant open
            day-28 to close day-2), the month-open four-hour window, and the
            conditional weekend window gated on the trailing 7d panel
            funding mean being at or under its trailing 365d median.

  ranks     cards 2 and 10: monthly rank diagnostics on the ten-name panel
            (common effective window): the realized-vol and volume-growth
            ranking keys, monthly side-flip turnover, and the Spearman
            correlation of each key against trailing returns.

Conventions, pinned exactly as the grade file pins them:

  * "gross 1x" reads as TOTAL gross of one: half long, half short on the
    L/S buckets (2 legs x 0.25 each side), full weight on long-only
    baskets. Every bps figure is on this unit.
  * funding is READ, never forecast: a decision at instant T uses prints in
    [T - lookback, T) only, and the NEXT settled rate is never a feature.
    A monthly book entered at the month's first open collects the prints in
    (M, M+1); the print AT M belongs to the predecessor position (the
    grade file's F1 settlement rule), so card eight's exit sits at the 09:00
    open to hold exactly one levy (08:00).
  * funding cash per settlement, bps of total gross = sum over legs of
    -side * weight * rate * 1e4, with side +1 long and -1 short: a long leg
    PAYs r when r > 0, a short leg COLLECTs r when r > 0.
  * the panel regime reading of cards four and six: the panel funding index
    is the equal-weight mean of the four majors' settled prints, anchored on
    BTC's print grid +-30 min; gate = index mean14 <= index median365
    (card four's declared default reading).
  * Determinism: no RNG. Known-answer parity check INSIDE the artifact: the
    monthly carry collection is computed twice (vectorized and looped) and
    the max abs difference is stored; any nonzero gap raises and the run
    refuses.

REGLA 0: every number the step-zero verdict cites must come from a persisted
artifact of this file (results/runs/q10diag-*.json), never from prose.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

FUND_SYMS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")
TEN_SYMS = FUND_SYMS + ("BNBUSDT", "LINKUSDT", "ADAUSDT", "DOGEUSDT",
                        "AVAXUSDT", "NEARUSDT")
MS_DAY = 86_400_000
MS_H = 3_600_000
BP = 10_000.0

# trailing-window print floors before a decision is used.
# Binance settles 3x/day, so expectations are 21 (7d), 43 (14d), 90 (30d),
# 1095 (365d); a symbol below the floor drops that decision.
MIN_7D, MIN_14D, MIN_30D, MIN_365D = 18, 40, 80, 950


# ---------------------------------------------------------------- loaders
def _load_klines(path: str) -> dict:
    df = pd.read_csv(path)
    df = df.sort_values("open_ts").reset_index(drop=True)
    return {"t": np.asarray(df["open_ts"], dtype=np.int64),
            "o": np.asarray(df["open"], dtype=float),
            "c": np.asarray(df["close"], dtype=float),
            "v": np.asarray(df["volume"], dtype=float)}


def _load_funding(path: str) -> tuple:
    recs = json.load(open(path, encoding="utf-8"))
    idx = pd.DatetimeIndex(pd.to_datetime([int(x["t"]) for x in recs],
                                          unit="ms", utc=True)).as_unit("ms")
    r = pd.Series([float(x["r"]) for x in recs], index=idx)
    r = r[~r.index.duplicated(keep="last")].sort_index()
    return np.asarray(idx.asi8, dtype=np.int64), np.asarray(r.values, float)


def _by_base(paths) -> dict:
    return {os.path.basename(p): p for p in paths}


def _c_before(k, t):
    """Close of the last bar with open_ts < t (the 'close on day X' mark)."""
    i = int(np.searchsorted(k["t"], t, side="left")) - 1
    return float(k["c"][i]) if i >= 0 else None


def _open_at(k, t):
    """Open of the bar stamped exactly t, else a print within +-2 h."""
    i = int(np.searchsorted(k["t"], t, side="left"))
    if i >= len(k["t"]):
        return None
    for j in (i, i - 1):
        if j >= 0 and abs(k["t"][j] - t) <= 2 * MS_H:
            return float(k["o"][j])
    return None


def _r_print(ts, r, t, slack_ms=1_800_000):
    """The settled print at instant t (within +slack)."""
    i = int(np.searchsorted(ts, t, side="left"))
    if i < len(ts) and ts[i] - t <= slack_ms:
        return float(r[i])
    return None


def _fstats(ts, r, t, days):
    """(n prints, mean, median) over [t - days, t); None when empty."""
    hi = int(np.searchsorted(ts, t, side="left"))
    lo = int(np.searchsorted(ts, t - days * MS_DAY, side="left"))
    if hi <= lo:
        return None
    seg = r[lo:hi]
    return hi - lo, float(seg.mean()), float(np.median(seg))


def _d7(ts, r, t):
    """Settled-rate change over trailing 7 days via prints strictly < t."""
    hi = int(np.searchsorted(ts, t, side="left")) - 1
    lo = int(np.searchsorted(ts, t - 7 * MS_DAY, side="left"))
    if hi < 0 or hi < lo or (hi - lo + 1) < MIN_7D:
        return None
    return float(r[hi] - r[lo])


def _month_starts(t_lo, t_hi) -> list:
    """UTC first-ms of every month start inside (t_lo, t_hi).

    pd.Period.start_time returns a tz-NAIVE stamp even from a tz-aware
    anchor, so every start is re-localized to UTC before use (naive
    .timestamp() would assume local time and shift by hours on Windows).
    """
    a = pd.Timestamp(int(t_lo), unit="ms", tz="UTC")
    b = pd.Timestamp(int(t_hi), unit="ms", tz="UTC")
    out = []
    p = pd.Period(a, "M")
    while True:
        s = p.start_time.tz_localize("UTC")
        if s >= b:
            break
        if s > a:
            out.append(s)
        p += 1
    return [int(s.timestamp() * 1000) for s in out]


def _prev_month_start(m0: int) -> int:
    ts = pd.Timestamp(m0, unit="ms", tz="UTC")
    return int(((ts.to_period("M") - 1).start_time
                .tz_localize("UTC").timestamp() * 1000))


def _next_month_ms(m0: int) -> int:
    s = (pd.Timestamp(m0, unit="ms", tz="UTC")
         + pd.offsets.MonthBegin(1))
    return int(s.timestamp() * 1000)


def _spearman(a, b) -> float:
    s = float(pd.Series(a).corr(pd.Series(b), method="spearman"))
    return s if s == s else float("nan")


def _median_run(flags) -> float:
    """Median consecutive-run length (in decision units) of 1-states."""
    runs, cur = [], 0
    for f in flags:
        if f:
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    return float(np.median(runs)) if runs else 0.0


def _by_year_ceil(vals, month_labels) -> str:
    agg = {}
    for v, lbl in zip(vals, month_labels):
        agg.setdefault(int(lbl[:4]), []).append(v)
    return "|".join(f"{y}:{float(np.median(x)):.2f}"
                    for y, x in sorted(agg.items()))


def _panel_funding(fund: dict, anchor: str = "BTCUSDT") -> tuple:
    """Equal-weight mean of the four majors' settled prints on the anchor's
    print grid, +-30 min alignment. Returns (ts_ms, panel_rate, full_share):
    only anchors where ALL FOUR symbols are present inside the window get a
    panel rate (full_share reports how often that held)."""
    ts0, _ = fund[anchor]
    missing = np.zeros(len(ts0), dtype=int)
    total = np.zeros(len(ts0), dtype=float)
    for sym in FUND_SYMS:
        tss, rr = fund[sym]
        j0 = np.searchsorted(tss, ts0 - 1_800_000, side="left")
        j1 = np.searchsorted(tss, ts0 + 1_800_000, side="left")
        have = j1 > j0
        missing += (~have).astype(int)
        mid = (j0 + j1 - 1) // 2          # middle print inside the window
        total[have] += rr[mid[have]]
    full = missing == 0
    panel = total[full] / float(len(FUND_SYMS))
    full_share = float(np.mean(full))
    return ts0[full], panel, full_share


def _self_checks(fund: dict, kl: dict) -> dict:
    """Coverage assertion: the AGENTS funding lesson, measured, not assumed."""
    out = {}
    for sym in FUND_SYMS:
        ts, _ = fund[sym]
        days = (ts[-1] - ts[0]) / MS_DAY
        out[f"fund_prints_per_day_{sym}"] = float(len(ts) / (days + 1.0))
    for sym in FUND_SYMS:
        out[f"klines_median_gap_min_{sym}"] = float(
            np.median(np.diff(kl[sym]["t"])) / 60_000)
    return out


def _monthly_collection(fund: dict, m0: int, m1: int,
                        long_s: set, short_s: set) -> tuple:
    """Funding cash over (m0, m1) in bps of total gross for the declared
    buckets. Computed vectorized and by explicit loop; both values and their
    max abs difference are returned (parity check)."""
    w = 0.25
    keys = []
    for sym in FUND_SYMS:
        ts, rr = fund[sym]
        i0 = int(np.searchsorted(ts, m0, side="right"))
        i1 = int(np.searchsorted(ts, m1, side="left"))
        side = -1.0 if sym in short_s else 1.0
        keys.append((ts, rr, i0, i1, side))
    vec = sum(-side * w * float(rr[i0:i1].sum())
              for ts, rr, i0, i1, side in keys if i1 > i0)
    lp = 0.0
    for ts, rr, i0, i1, side in keys:
        for i in range(i0, i1):
            lp += -side * w * float(rr[i])
    return vec * BP, abs(vec - lp) * BP


def _price_diff(kl: dict, m0: int, m1: int, long_s: set, short_s: set):
    """(0.25 x sum long log-rets - 0.25 x sum short log-rets) in bps."""
    rets = {}
    for sym in FUND_SYMS:
        c0, c1 = _c_before(kl[sym], m0), _c_before(kl[sym], m1)
        if c0 is None or c1 is None or c0 <= 0 or c1 <= 0:
            return None
        rets[sym] = float(np.log(c1 / c0))
    return float((sum(rets[s] for s in long_s)
                  - sum(rets[s] for s in short_s)) * 0.25 * BP)


def _summary(vals) -> tuple:
    """(median, mean, positive share) over finite values; NaN triplet if empty."""
    v = np.asarray([x for x in vals if x == x], float)
    if not len(v):
        return float("nan"), float("nan"), float("nan")
    return float(np.median(v)), float(v.mean()), float((v > 0).mean())


def _mean_of(vals) -> float:
    v = [x for x in vals if x == x]
    return float(np.mean(v)) if v else float("nan")


def _median_of(vals) -> float:
    v = [x for x in vals if x == x]
    return float(np.median(v)) if v else float("nan")


# ------------------------------------------------------------ funding mode
def _run_funding(paths) -> tuple:
    b = _by_base(paths)
    fund = {s: _load_funding(b[f"{s}_funding.json"]) for s in FUND_SYMS}
    kl = {s: _load_klines(b[f"{s}_1h.csv"]) for s in FUND_SYMS}
    metrics = {"mode": "funding"}
    metrics.update(_self_checks(fund, kl))

    t_hi = min(min(int(fund[s][0][-1]) for s in FUND_SYMS),
               min(int(kl[s]["t"][-1]) for s in FUND_SYMS))
    t_lo = max(int(fund[s][0][0]) for s in FUND_SYMS)
    months = _month_starts(t_lo + 30 * MS_DAY, t_hi)

    rows1, rows5, rows8, staleness, parity, side_agree = [], [], [], [], [], []
    for m0 in months:
        m1 = _next_month_ms(m0)
        if t_hi < m1 - MS_H:
            break
        d7, avg30 = {}, {}
        ok = True
        for sym in FUND_SYMS:
            ts, rr = fund[sym]
            if ts[0] > m0 - 30 * MS_DAY:
                ok = False
                break
            s7 = _d7(ts, rr, m0)
            st30 = _fstats(ts, rr, m0, 30)
            if s7 is None or st30 is None or st30[0] < MIN_30D:
                ok = False
                break
            d7[sym], avg30[sym] = s7, st30[1]
        if not ok:
            continue

        lbl = pd.Timestamp(m0, unit="ms", tz="UTC").strftime("%Y-%m")
        for key, rows in ((d7, rows1), (avg30, rows5)):
            order = sorted(FUND_SYMS, key=lambda s: (key[s], s))
            long2, short2 = set(order[:2]), set(order[2:])
            cash, pgap = _monthly_collection(fund, m0, m1, long2, short2)
            parity.append(pgap)
            price = _price_diff(kl, m0, m1, long2, short2)
            combined = cash + price if price is not None else float("nan")
            rows.append({"month": lbl,
                         "long": ",".join(sorted(long2)),
                         "short": ",".join(sorted(short2)),
                         "cash_bps": cash,
                         "price_bps": price if price is not None else float("nan"),
                         "combined_bps": combined})

        # rank staleness: decision-time delta ranks vs realized next-month
        # mean settled rate ranks (what the shorts will actually face)
        real = {}
        for sym in FUND_SYMS:
            ts, rr = fund[sym]
            i0 = int(np.searchsorted(ts, m0, side="right"))
            i1 = int(np.searchsorted(ts, m1, side="left"))
            real[sym] = float(rr[i0:i1].mean()) if i1 > i0 else float("nan")
        staleness.append(_spearman([d7[s] for s in FUND_SYMS],
                                   [real[s] for s in FUND_SYMS]))

        # card eight settlement-hour episodes, all four symbols
        signs = []
        for sym in FUND_SYMS:
            s = 1.0 if avg30[sym] < 0 else -1.0
            signs.append(s)
            entry = _open_at(kl[sym], m0)
            exit_ = _open_at(kl[sym], m0 + 9 * MS_H)
            levy = _r_print(fund[sym][0], fund[sym][1], m0 + 8 * MS_H)
            if entry is None or exit_ is None or levy is None or entry <= 0:
                continue
            move = s * float(np.log(exit_ / entry)) * BP
            levy_bps = -s * levy * BP
            rows8.append({"month": lbl, "sym": sym,
                          "side": "long" if s > 0 else "short",
                          "move_bps": move, "levy_bps": levy_bps,
                          "fav_bps": move + levy_bps})
        side_agree.append(bool(len(set(signs)) == 1))

    # card four: biweekly panel regime gate on the panel funding index
    p_ts, p_r, full_share = _panel_funding(fund)
    dec_ms, rows4 = [], []
    t0 = (p_ts[0] // MS_DAY) * MS_DAY
    while t0 + 14 * MS_DAY <= p_ts[-1]:
        st14 = _fstats(p_ts, p_r, t0, 14)
        st365 = _fstats(p_ts, p_r, t0, 365)
        if st14 is not None and st14[0] >= MIN_14D \
           and st365 is not None and st365[0] >= MIN_365D:
            dec_ms.append((t0, bool(st14[1] <= st365[2])))
        t0 += 14 * MS_DAY
    for t0, g in dec_ms:
        rows4.append({"decision": pd.Timestamp(t0, unit="ms",
                                               tz="UTC").strftime("%Y-%m-%d"),
                      "gate_long": g})
    states4 = [g for _, g in dec_ms]
    years4 = {}
    for (t0, g) in dec_ms:
        years4.setdefault(int(pd.Timestamp(t0, unit="ms", tz="UTC").year),
                          []).append(g)
    yr4 = "|".join(f"{y}:{100.0 * float(np.mean(v)):.1f}"
                   for y, v in sorted(years4.items()))

    c1f, m1f, p1f = _summary([r["cash_bps"] for r in rows1])
    c1p, m1p, p1p = _summary([r["price_bps"] for r in rows1])
    c1c, m1c, _ = _summary([r["combined_bps"] for r in rows1])
    c5f, m5f, p5f = _summary([r["cash_bps"] for r in rows5])
    c5p, m5p, p5p = _summary([r["price_bps"] for r in rows5])
    c5c, m5c, _ = _summary([r["combined_bps"] for r in rows5])
    cf8, mf8, pf8 = _summary([r["fav_bps"] for r in rows8])
    cl8, ml8, _ = _summary([r["levy_bps"] for r in rows8])
    st_arr = np.asarray([x for x in staleness if x == x], float)
    in_mkt = float(np.mean(states4)) if states4 else float("nan")
    n_long8 = sum(1 for r in rows8 if r["side"] == "long")

    metrics.update({
        "n_months_scored": len(rows1),
        "card1_funding_median_bps_month": c1f, "card1_funding_mean_bps": m1f,
        "card1_funding_pos_share": p1f,
        "card1_price_median_bps": c1p, "card1_price_mean_bps": m1p,
        "card1_price_pos_share": p1p,
        "card1_combined_median_bps": c1c, "card1_combined_mean_bps": m1c,
        "card1_funding_by_year_median": _by_year_ceil(
            [r["cash_bps"] for r in rows1], [r["month"] for r in rows1]),
        "card1_rank_staleness_median_spearman":
            float(np.median(st_arr)) if len(st_arr) else float("nan"),
        "card5_funding_median_bps_month": c5f, "card5_funding_mean_bps": m5f,
        "card5_funding_pos_share": p5f,
        "card5_price_median_bps": c5p, "card5_price_mean_bps": m5p,
        "card5_price_pos_share": p5p,
        "card5_combined_median_bps": c5c, "card5_combined_mean_bps": m5c,
        "card5_funding_by_year_median": _by_year_ceil(
            [r["cash_bps"] for r in rows5], [r["month"] for r in rows5]),
        "card8_episodes": len(rows8),
        "card8_fav_median_bps": cf8, "card8_fav_mean_bps": mf8,
        "card8_fav_pos_share": pf8,
        "card8_levy_median_bps": cl8, "card8_levy_mean_bps": ml8,
        "card8_long_share": float(n_long8 / max(1, len(rows8))),
        "card8_months_all_sides_agree_share":
            float(np.mean(side_agree)) if side_agree else float("nan"),
        "card4_n_decisions": len(dec_ms),
        "card4_panel_index_full_coverage_share": full_share,
        "card4_in_market_pct": 100.0 * in_mkt if in_mkt == in_mkt else float("nan"),
        "card4_median_long_spell": _median_run(states4),
        "card4_in_market_by_year_pct": yr4,
        # pre-declared kill bars (grade file, Step zero section)
        "KILL_card5_carry_median_lt_22bps": bool(c5f == c5f and c5f < 22.0),
        "KILL_card4_in_market_out_of_band":
            bool(in_mkt == in_mkt and (in_mkt < 0.25 or in_mkt > 0.75)),
        "KILL_card8_fav_median_lt_half_demand":
            bool(cf8 == cf8 and cf8 < 11.5),
        "parity_max_abs_diff_bps": float(np.max(parity)) if parity else 0.0,
    })
    if metrics["parity_max_abs_diff_bps"] > 1e-9:
        raise ValueError("q10diag funding: collection parity check FAILED "
                         f"(max abs diff {metrics['parity_max_abs_diff_bps']} bps)")

    prov = {"adapter": "q10diag", "engine_version": "q10diag-1",
            "mode": "funding",
            "conventions": {
                "gross1x": "total gross of one; L/S buckets 2 legs x 0.25 per side",
                "feature_window": "prints in [T-lookback, T) only",
                "collection_window": "prints in (M, M+1); the print at M is not ours",
                "card8_exit": "09:00 open: exactly one levy (08:00), grade pin F1",
                "bps_unit": "bps of total gross; log price basis",
                "card4_gate": "panel funding index (equal-weight mean of the four "
                              "majors' prints, BTC-anchored +-30 min); gate = "
                              "index mean14 <= index median365",
            },
            "kill_bars": {
                "card5": "median monthly carry collection < 22 bps",
                "card4": "in-market fraction < 25% or > 75%",
                "card8": "median favorable move < 11.5 bps (half the 23 bps demand)",
            },
            "note": "descriptive only; no costs, no strategy returns"}
    return metrics, prov, rows1 + rows5 + rows8 + rows4


# ----------------------------------------------------------- calendar mode
def _run_calendar(paths) -> tuple:
    b = _by_base(paths)
    kl = {s: _load_klines(b[f"{s}_1h.csv"]) for s in FUND_SYMS}
    fund = {s: _load_funding(b[f"{s}_funding.json"]) for s in FUND_SYMS}
    metrics = {"mode": "calendar"}
    metrics.update(_self_checks(fund, kl))

    lo = max(int(kl[s]["t"][0]) for s in FUND_SYMS)
    hi = min(int(kl[s]["t"][-1]) for s in FUND_SYMS)
    months = _month_starts(lo + 31 * MS_DAY, hi)

    rows3, rows7, rows6 = [], [], []
    for m0 in months:
        m1 = _next_month_ms(m0)
        if hi < m1 - MS_H:
            break
        lbl = pd.Timestamp(m0, unit="ms", tz="UTC").strftime("%Y-%m")
        day28_prev = _prev_month_start(m0) + 27 * MS_DAY
        day3_this = m0 + 2 * MS_DAY
        # card three: BTC/ETH basket, declared window and fill-t+1 variant
        e_i, e_t, ok3 = [], [], True
        for sym in ("BTCUSDT", "ETHUSDT"):
            if kl[sym]["t"][0] > day28_prev - 2 * MS_DAY:
                ok3 = False
                break
            c_in = _c_before(kl[sym], day28_prev)
            c_out = _c_before(kl[sym], day3_this)
            o_in = _open_at(kl[sym], day28_prev)
            if c_in is None or c_out is None or o_in is None:
                ok3 = False
                break
            e_i.append(float(np.log(c_out / c_in)))
            e_t.append(float(np.log(c_out / o_in)))
        if ok3:
            rows3.append({"month": lbl,
                          "declared_bps": float(np.mean(e_i) * BP),
                          "t1_bps": float(np.mean(e_t) * BP)})
        # card seven: month-open four-hour window, four-name basket
        rs7, ok7 = [], True
        for sym in FUND_SYMS:
            o_in = _open_at(kl[sym], m0)
            o_out = _open_at(kl[sym], m0 + 4 * MS_H)
            if o_in is None or o_out is None or o_in <= 0:
                ok7 = False
                break
            rs7.append(float(np.log(o_out / o_in)))
        if ok7:
            rows7.append({"month": lbl, "basket_bps": float(np.mean(rs7) * BP)})

    # card six: conditional weekend windows on Fridays, four-name basket
    p_ts, p_r, full6 = _panel_funding(fund)
    metrics["card6_panel_index_full_coverage_share"] = full6
    fri = (p_ts[0] // MS_DAY) * MS_DAY
    while pd.Timestamp(fri, unit="ms", tz="UTC").dayofweek != 4:
        fri += MS_DAY
    while fri + 3 * MS_DAY <= hi:
        ts_dec = fri + 12 * MS_H
        st7 = _fstats(p_ts, p_r, ts_dec, 7)
        st365 = _fstats(p_ts, p_r, ts_dec, 365)
        if st7 is not None and st365 is not None \
           and st7[0] >= MIN_7D and st365[0] >= MIN_365D:
            gate = bool(st7[1] <= st365[2])
            mon_ms = fri + 3 * MS_DAY          # Friday 00:00 + 3 d = Monday 00:00
            rs, ok6 = [], True
            for sym in FUND_SYMS:
                o_in = _open_at(kl[sym], fri + 13 * MS_H)
                c_out = _c_before(kl[sym], mon_ms)
                if o_in is None or c_out is None or o_in <= 0:
                    ok6 = False
                    break
                rs.append(float(np.log(c_out / o_in)))
            if ok6:
                rows6.append({"week": pd.Timestamp(fri, unit="ms", tz="UTC")
                              .strftime("%Y-%m-%d"),
                              "gate_long": gate,
                              "ret_bps": float(np.mean(rs) * BP)})
        fri += 7 * MS_DAY

    d3a = [r["declared_bps"] for r in rows3]
    d3t = [r["t1_bps"] for r in rows3]
    d7v = [r["basket_bps"] for r in rows7]
    act = [r["ret_bps"] for r in rows6 if r["gate_long"]]
    all6 = [r["ret_bps"] for r in rows6]

    m3d, m3t, m7m = _mean_of(d3a), _mean_of(d3t), _mean_of(d7v)
    m6a, m6c = _mean_of(act), _mean_of(all6)
    metrics.update({
        "n_months_card3": len(rows3), "n_months_card7": len(rows7),
        "n_weekends_card6": len(rows6),
        "card6_active_share_pct": 100.0 * len(act) / max(1, len(rows6)),
        "card3_mean_declared_bps": m3d, "card3_mean_t1_bps": m3t,
        "card3_median_t1_bps": _median_of(d3t),
        "card7_mean_bps": m7m, "card7_median_bps": _median_of(d7v),
        "card6_cond_mean_bps": m6a, "card6_uncond_mean_bps": m6c,
        "card6_cond_median_bps": _median_of(act),
        # pre-declared kill bars
        "KILL_card3_t1_mean_lt_18bps": bool(m3t == m3t and m3t < 18.0),
        "KILL_card7_mean_lt_12bps": bool(m7m == m7m and m7m < 12.0),
        "KILL_card6_cond_mean_lt_12bps": bool(m6a == m6a and m6a < 12.0),
    })
    prov = {"adapter": "q10diag", "engine_version": "q10diag-1",
            "mode": "calendar",
            "conventions": {
                "card3": "declared = close day-27 -> close day-2; t1 = open "
                         "day-28 -> close day-2 (the executable fill-t+1 variant)",
                "card7": "entry open of the month's first 1h bar, exit open of "
                         "the 04:00 bar",
                "card6": "decision Fri 12:00 (prints < T); entry open Fri 13:00; "
                         "exit close before Monday 00:00; four-name basket; gate "
                         "on the panel funding index (mean7 <= median365)",
                "bps_unit": "bps on total gross 1x; log price basis",
            },
            "kill_bars": {
                "card3": "fill-t+1 window mean < 18 bps",
                "card7": "four-hour window mean < 12 bps",
                "card6": "gated weekend mean < 12 bps",
            },
            "note": "descriptive only; no costs, no strategy returns"}
    return metrics, prov, rows3 + rows6 + rows7


# --------------------------------------------------------------- ranks mode
def _run_ranks(paths) -> tuple:
    b = _by_base(paths)
    kl = {}
    for s in TEN_SYMS:
        k = _load_klines(b[f"{s}_1h.csv"])
        k["lr"] = np.diff(np.log(k["c"]))
        kl[s] = k
    lo = max(int(k["t"][0]) for k in kl.values())
    hi = min(int(k["t"][-1]) for k in kl.values())
    months = _month_starts(lo + 190 * MS_DAY, hi)

    rows = []
    prev_sides = {"vol": {}, "growth": {}}
    flips = {"vol": [], "growth": []}
    sp_vol, sp_growth = [], []
    for m0 in months:
        keyv, ok = {"vol": {}, "growth": {}, "ret": {}}, True
        for sym in TEN_SYMS:
            k = kl[sym]
            i = int(np.searchsorted(k["t"], m0, side="left"))
            if i < 4320 or (i - 1) >= len(k["lr"]):
                ok = False
                break
            r720 = k["lr"][i - 720:i - 1]
            v720 = k["v"][i - 720:i - 1]
            v180 = k["v"][i - 4320:i - 1]
            if len(r720) < 690 or np.mean(v180) <= 0:
                ok = False
                break
            keyv["vol"][sym] = float(np.std(r720, ddof=1))
            keyv["ret"][sym] = float(np.mean(r720))
            keyv["growth"][sym] = float(np.mean(v720) / np.mean(v180))
        if not ok:
            continue
        lbl = pd.Timestamp(m0, unit="ms", tz="UTC").strftime("%Y-%m")
        row = {"month": lbl}
        for field in ("vol", "growth"):
            order = sorted(TEN_SYMS, key=lambda s: (keyv[field][s], s))
            long5, short5 = order[:5], order[5:]
            sided = {s: (1 if s in long5 else -1) for s in TEN_SYMS}
            flips[field].append(int(sum(1 for s in TEN_SYMS
                                        if prev_sides[field].get(s) != sided[s]))
                                / float(len(TEN_SYMS)))
            prev_sides[field] = sided
            row[f"long_{field}"] = ",".join(long5)
            row[f"short_{field}"] = ",".join(short5)
        sp_vol.append(_spearman(list(keyv["vol"].values()),
                                list(keyv["ret"].values())))
        sp_growth.append(_spearman(list(keyv["growth"].values()),
                                   list(keyv["ret"].values())))
        rows.append(row)

    sv = np.asarray([x for x in sp_vol if x == x], float)
    sg = np.asarray([x for x in sp_growth if x == x], float)
    fv = np.asarray(flips["vol"], float)
    fg = np.asarray(flips["growth"], float)
    metrics = {
        "mode": "ranks",
        "n_months": len(rows),
        "klines_median_gap_min": float(np.median(np.diff(
            kl["BTCUSDT"]["t"])) / 60_000),
        "months_window": (f"{rows[0]['month']}..{rows[-1]['month']}"
                          if rows else "none"),
        "card2_monthly_flip_share_median":
            float(np.median(fv)) if len(fv) else float("nan"),
        "card10_monthly_flip_share_median":
            float(np.median(fg)) if len(fg) else float("nan"),
        "card2_spearman_vol_vs_trailing_ret_median":
            float(np.median(sv)) if len(sv) else float("nan"),
        "card2_spearman_abs_gt_half_share":
            float(np.mean(np.abs(sv) > 0.5)) if len(sv) else float("nan"),
        "card10_spearman_growth_vs_trailing_ret_median":
            float(np.median(sg)) if len(sg) else float("nan"),
        "card10_spearman_abs_gt_half_share":
            float(np.mean(np.abs(sg) > 0.5)) if len(sg) else float("nan"),
    }
    prov = {"adapter": "q10diag", "engine_version": "q10diag-1", "mode": "ranks",
            "conventions": {
                "vol_key": "std of 1h log returns, trailing 720 bars "
                           "(annualization constant omitted: rank-invariant)",
                "growth_key": "mean volume trailing 720 bars / mean volume "
                              "trailing 4320 bars",
                "ret_key": "diagnostic only: mean of the same 720 log returns",
                "ranks": "ties broken by symbol name (deterministic)",
                "common_window": "months need 4320 bars of history in all ten names",
            },
            "note": "descriptive only; no costs, no returns, no kill bars"}
    return metrics, prov, rows


def run(mode: str, paths: list):
    if mode == "funding":
        return _run_funding(paths)
    if mode == "calendar":
        return _run_calendar(paths)
    if mode == "ranks":
        return _run_ranks(paths)
    raise ValueError(f"unknown q10diag mode: {mode!r}")
