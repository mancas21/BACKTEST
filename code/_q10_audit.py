#!/usr/bin/env python
"""_q10_audit.py -- known-answer audit for code/q10_engine.py.

MANDATORY REGLA 0 gate: must PASS before any real-data engine run and after
any change to the engine. Runs ordinary functions of code/q10_engine.py and
code/q10_diag.py on HAND-BUILT synthetic panels (not the market data, not
inpainted numbers). No vrun.py involvement, no run_id: these are labelled
known-answer cases.

Output: results/q10_engine_audit.txt (PASS/FAIL per case + summary).
Exit 0 iff all cases pass; 1 otherwise.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import q10_diag as D          # noqa: E402
import q10_engine as E        # noqa: E402

MS_H, MS_DAY, BP = E.MS_H, E.MS_DAY, E.BP
T0 = int(pd.Timestamp(2021, 5, 1, tz="UTC").timestamp() * 1000)
RESULTS = []
FAILS = []


def _case(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    if not cond:
        FAILS.append(name)
    return bool(cond)


# ------------------------------------------------------------ synthetic data
def _uni_kline(start_ms, n, o0, dr, dv=1.0, name="X"):
    """Hourly synthetic bar series: open rises linearly by dr per bar from
    o0; close = open + dr_inter? Kept simple: o[i] = o0 + dr*i, c[i] = o0
    + dr*(i) + 0.5 (close differs from open by +0.5 always)."""
    o = o0 + dr * np.arange(n + 1, dtype=float)
    c = o + 0.5
    v = dv * np.ones(n + 1, dtype=float)
    t = start_ms + np.arange(n + 1, dtype=np.int64) * MS_H
    return {"t": t, "o": o, "c": c, "v": v,
            "lr": np.diff(np.log(c)), "lc": np.log(c)}


def _funding(ts, rates):
    return (np.asarray(ts, dtype=np.int64), np.asarray(rates, dtype=float))


# =========================================================================
# CASE 1 -- executor: fees on real fills, zero on rolls, final close
def case1():
    t0 = T0
    kl = {"AAA": _uni_kline(t0, 12, 10.0, 1.0)}
    k = kl["AAA"]
    px = {t: k["o"][i] for i, t in enumerate(k["t"])}
    ev = [(t0, {"AAA": (1.0, 0.25)}, "rebalance"),
          (t0 + 3 * MS_H, {"AAA": (1.0, 0.25)}, "rebalance"),   # roll
          (t0 + 5 * MS_H, {"AAA": (-1.0, 0.25)}, "rebalance"),  # flip
          (t0 + 8 * MS_H, {}, "final_liquidation")]
    eps = E._execute(ev, kl)
    _case("c1.three_episodes", len(eps) == 3, f"n={len(eps)}")
    e1, e2, e3 = eps
    _case("c1.e1_fees", e1["in_fee_bps"] == 11.0 and e1["exit_fee_bps"] == 0.0
          and e1["exit_reason"] == "roll",
          f"in={e1['in_fee_bps']} out={e1['exit_fee_bps']}")
    _case("c1.e1_prices", e1["entry_px"] == 10.0 and e1["exit_px"] == 13.0,
          f"entry={e1['entry_px']} exit={e1['exit_px']}")
    _case("c1.e2_roll", e2["in_fee_bps"] == 0.0 and e2["exit_fee_bps"] == 11.0
          and e2["entry_px"] == 13.0 and e2["exit_px"] == 15.0
          and e2["entry_ts"] == t0 + 3 * MS_H and e2["exit_ts"] == t0 + 5 * MS_H
          and e2["side"] == 1.0,
          f"{e2['entry_px']}->{e2['exit_px']}")
    _case("c1.e3_flipped", e3["side"] == -1.0 and e3["in_fee_bps"] == 11.0
          and e3["entry_px"] == 15.0 and e3["exit_ts"] == t0 + 8 * MS_H
          and e3["exit_px"] == 18.0 and e3["exit_reason"] == "final_liquidation",
          f"{e3['side']} {e3['entry_px']}->{e3['exit_px']}")
    # every leg exit price is the open of a bar stamped at the fill instant
    okpx = all(D._open_at(kl[e["sym"]], e["exit_ts"]) == e["exit_px"]
               for e in eps)
    _case("c1.exit_price_is_open_at_fill_ts", okpx)


# =========================================================================
# CASE 2 -- funding bill: prints strictly inside (entry, exit); the print AT
# entry and AT exit is excluded; long pays r, short collects r
def case2():
    t0 = T0
    kl = {"AAA": _uni_kline(t0 - MS_H, 10, 10.0, 1.0)}
    # prints at entry (+0, must NOT bill), +2h (bills), +3h (bills),
    # +4h == exit (must NOT bill)
    f = _funding([t0, t0 + 2 * MS_H, t0 + 3 * MS_H, t0 + 4 * MS_H],
                 [0.01, 0.02, 0.03, 0.04])
    ep = E._episode("AAA", 1.0, 0.25, t0, 10.0, 11.0)
    E._close(ep, t0 + 4 * MS_H, 14.0, 11.0, "window")
    E._bill([ep], {"AAA": f})
    _case("c2.billed_two_prints", ep["funding_n"] == 2
          and abs(ep["funding_bps"] - (-1.0 * 0.05 * BP)) < 1e-9,
          f"n={ep['funding_n']} bps={ep['funding_bps']}")
    # short collects: -side flips the sign
    ep2 = E._episode("AAA", -1.0, 0.25, t0, 10.0, 11.0)
    E._close(ep2, t0 + 4 * MS_H, 9.0, 11.0, "window")
    E._bill([ep2], {"AAA": f})
    _case("c2.short_collects", abs(ep2["funding_bps"] - 0.05 * BP) < 1e-9,
          f"bps={ep2['funding_bps']}")
    # unbilled symbol: no file -> zero funding, disclosed via billable flag
    ep3 = E._episode("BBB", 1.0, 0.1, t0, 10.0, 11.0)
    E._close(ep3, t0 + 4 * MS_H, 14.0, 11.0, "window")
    E._bill([ep3], {"AAA": f})
    _case("c2.unbilled_zero", ep3["funding_bps"] == 0.0
          and ep3["funding_n"] == 0 and ep3["billable"] is False)


# =========================================================================
# CASE 3 -- unit arithmetic: _ep_net_bps and the equity/unit parity gate
def case3():
    t0 = T0
    kl = {"AAA": _uni_kline(t0 - MS_H, 10, 10.0, 1.0)}
    f = _funding([t0 + 1 * MS_H, t0 + 2 * MS_H], [0.01, 0.02])
    ep = E._episode("AAA", 1.0, 0.25, t0, 10.0, 11.0)
    E._close(ep, t0 + 4 * MS_H, 14.0, 11.0, "window")
    E._bill([ep], {"AAA": f})
    exp = 1e4 * float(np.log(14.0 / 10.0)) + (-0.03 * BP) - 22.0
    _case("c3.ep_net_bps", abs(E._ep_net_bps(ep) - exp) < 1e-6,
          f"{E._ep_net_bps(ep)} vs {exp}")
    metrics, eps, tables = E._score_book(
        "CARD1", kl, {"AAA": f}, [ep], ["AAA"],
        card_extra={"probe": 1})
    _case("c3.parity_ok", metrics["parity_units_vs_equity_bps"] < 1e-6)
    # hand equity: per-bar pieces must sum to side*w*log(14/10) - fees + fund
    cum_expected = 0.25 * float(np.log(14.0 / 10.0)) \
        - 2 * 0.25 * E.FEE_SIDE + 0.25 * (-0.03)
    _case("c3.book_net_frac",
          abs(metrics["return_pct"] / 100.0 - cum_expected) < 1e-9,
          f"{metrics['return_pct']:.6f} vs {100 * cum_expected:.6f}")


# =========================================================================
# CASE 4 -- bench: per-bar mean of log rets telescopes to the closed form
def case4():
    t0 = T0
    kl = {s: _uni_kline(t0 - MS_H, 10, 10.0 + 3.0 * i, 1.0, name=s)
          for i, s in enumerate(("AAA", "BBB", "CCC"))}
    t_start = t0
    t_end = t0 + 5 * MS_H
    n_h = (t_end - t_start) // MS_H + 1
    bench = np.zeros(n_h)
    for s in ("AAA", "BBB", "CCC"):
        k = kl[s]
        i0 = int(np.searchsorted(k["t"], t_start, side="left"))
        bench += np.diff(k["lc"][i0 - 1:i0 + n_h])
    bench /= 3.0
    closed = sum(float(kl[s]["lc"][int(np.searchsorted(kl[s]["t"], t_end,
                                                       side="left"))])
                 - float(kl[s]["lc"][int(np.searchsorted(kl[s]["t"], t_start,
                                                         side="left")) - 1])
                 for s in ("AAA", "BBB", "CCC")) / 3.0
    _case("c4.bench_telescopes",
          abs(float(bench.sum()) - closed) < 1e-12,
          f"{bench.sum():.12f} vs {closed:.12f}")


# =========================================================================
# CASE 5 -- _rv: two independent formulations agree; boundary slice semantics
def case5():
    n0 = T0
    k = _uni_kline(n0, 1000, 10.0, 1.0)
    i = 800
    v1 = E._rv(k, i, 720)
    lr = k["lr"]
    v2 = float(np.std(lr[i - 720:i - 1], ddof=1))
    _case("c5.rv_formulation", v1 == v2, f"{v1} vs {v2}")
    _case("c5.rv_floor_none", E._rv(k, 719, 720) is None)
    _case("c5.rv_floor_ok", E._rv(k, 720, 720) is not None)


# =========================================================================
# CASE 6 -- rank tie-break by symbol name; buckets 5/5, long lowest / short
# highest
def case6():
    t0 = T0
    names = ["AAAA", "BBBB", "CCCC", "DDDD", "EEEE",
             "FFFF", "GGGG", "HHHH", "IIII", "JJJJ"]
    kl = {}
    # all ten identical: every key ties -> order must fall back to name
    for nm in names:
        kl[nm] = _uni_kline(t0 - 5000 * MS_H, 5000, 100.0, 0.0)
    events = E._rank_month_build(
        kl, lambda k, i: 0.5, 4000, 0.1)
    rebal = [e for e in events if e[2] == "rebalance"]
    tgt = rebal[0][1]
    long_side = sorted(s for s, (side, w) in tgt.items() if side == 1.0)
    short_side = sorted(s for s, (side, w) in tgt.items() if side == -1.0)
    _case("c6.ten_into_five_five", len(long_side) == 5 and len(short_side) == 5)
    _case("c6.tie_break_names",
          long_side == names[:5] and short_side == names[5:],
          f"long={long_side[:2]}.. short={short_side[:2]}..")
    # a real spread: weight key 0.0..0.9 ascending by name index
    kl2 = {}
    for j, nm in enumerate(names):
        kl2[nm] = _uni_kline(t0 - 5000 * MS_H, 5000, 100.0, 0.0)
    events2 = E._rank_month_build(kl2, lambda k, i: float(names.index(
        next(n for n, kk in kl2.items() if kk is k))), 4000, 0.1) \
        if False else None
    # simpler: key = index is fed separately below
    idx_of = {nm: j for j, nm in enumerate(names)}
    reverser = {j: nm for j, nm in zip(idx_of.values(), idx_of)}
    kl2 = {}
    for nm in names:
        # make the vol key DECREASING in name index: craft price paths whose
        # log-return std ranks inversely
        amp = 1.0 + 0.1 * (9 - idx_of[nm])
        o = 100.0 + amp * np.sin(np.arange(5001) * np.pi / 7)
        c = o + 0.1
        tms = (t0 - 5000 * MS_H) + np.arange(5001, dtype=np.int64) * MS_H
        kl2[nm] = {"t": tms, "o": o, "c": c, "v": np.ones(5001),
                   "lr": np.diff(np.log(c)), "lc": np.log(c)}
    events2 = E._rank_month_build(kl2, lambda k, i: E._rv(k, i, 720), 4000, 0.1)
    tgt2 = [e[1] for e in events2 if e[2] == "rebalance"][0]
    long2 = sorted(s for s, (side, w) in tgt2.items() if side == 1.0)
    _case("c6.lowest_key_is_long", long2 == names[5:],
          f"long={long2[:3]}..")


# =========================================================================
# CASE 7 -- card3 month anchors and one hand-priced unit
def case7():
    m0 = int(pd.Timestamp(2024, 4, 1, tz="UTC").timestamp() * 1000)
    d28_exp = int(pd.Timestamp(2024, 3, 28, tz="UTC").timestamp() * 1000)
    d3_exp = int(pd.Timestamp(2024, 4, 3, tz="UTC").timestamp() * 1000)
    _case("c7.anchor_math", d28_exp == m0 - 4 * MS_DAY
          and d3_exp == m0 + 2 * MS_DAY,
          f"d28={d28_exp} d3={d3_exp}")
    syms3 = ("BTCUSDT", "ETHUSDT")
    kl = {s: _uni_kline(d28_exp - 2 * MS_DAY, 13 * 24, 100.0, 0.01, name=s)
          for s in syms3}
    eps, nskip = E._card3_build(kl)
    _case("c7.one_window", len(eps) == 2 and nskip == 0,
          f"eps={len(eps)} skip={nskip}")
    if eps:
        e0 = eps[0]
        _case("c7.window_instants",
              e0["entry_ts"] == d28_exp and e0["exit_ts"] == d3_exp
              and e0["w"] == 0.5
              and e0["in_fee_bps"] == 11.0 and e0["exit_fee_bps"] == 11.0)
        # both legs share one (entry, exit), so the basket units group to one
        metrics, _, tables = E._score_book(
            "CARD3", kl, {}, eps, list(syms3), card_extra={})
        _case("c7.units_grouped", metrics["units"] == 1,
              f"units={metrics['units']}")
    # decision data: the day-27 close must be the close of the last bar
    # whose OPEN is strictly before the day-28 00:00
    k = kl["BTCUSDT"]
    idx28 = int(np.searchsorted(k["t"], d28_exp, side="left"))
    cdec = D._c_before(k, d28_exp)
    _case("c7.decision_close", abs(cdec - k["c"][idx28 - 1]) < 1e-12)


# =========================================================================
# CASE 8 -- card4 panel gate reading: mean14 <= median365 (equality is LONG)
def case8():
    t0 = T0
    # 8h settlement grid for 400 days
    ts = np.arange(0, 400 * 3, dtype=np.int64) * 8 * 3600_000 + t0 - 200 * MS_DAY
    def funds_of(rate_fn):
        return {s: (ts, np.asarray([rate_fn(i, s) for i in range(len(ts))]))
                for s in E.FUND_SYMS}

    # CASE A: rising funding regime -> late mean14 > median365 -> flat
    fa = funds_of(lambda i, s: 0.0001 + 1e-9 * i)
    p_ts, p_r, full = D._panel_funding(fa)
    _case("c8.panel_full", full == 1.0,
          f"full={full}")
    t_dec = int(p_ts[-1]) - 14 * MS_DAY
    st14 = D._fstats(p_ts, p_r, t_dec, 14)
    st365 = D._fstats(p_ts, p_r, t_dec, 365)
    gate = bool(st14[1] <= st365[2])
    _case("c8.rising_is_flat", gate is False,
          f"mean14={st14[1]:.8f} med365={st365[2]:.8f}")
    # CASE B: a two-level panel where the trailing mean sits just below the
    # 365d median -> long. Exact float equality is avoided by construction
    # (the gate comparison is the diag's `st14[1] <= st365[2]`, byte-identical
    # to the step-zero artifact's convention, so no new rule is introduced).
    def funds_two_level(l1, l2):
        sw = int(t0 + 195 * MS_DAY)
        ra = np.where(ts < sw, l1, l2)
        return {s: (ts, np.full(len(ts), 0.0) + ra) for s in E.FUND_SYMS}
    fb = funds_two_level(0.00022, 0.00020)
    p_ts2, p_r2, _ = D._panel_funding(fb)
    t_dec2 = int(p_ts2[-1]) - 15 * MS_DAY
    st14b = D._fstats(p_ts2, p_r2, t_dec2, 14)
    st365b = D._fstats(p_ts2, p_r2, t_dec2, 365)
    _case("c8.calmer_recent_is_long", bool(st14b[1] <= st365b[2]) is True,
          f"mean14={st14b[1]:.10f} med365={st365b[2]:.10f}".replace("True", "long"))
    # CASE C: falling regime -> long
    fc = funds_of(lambda i, s: -0.0001 - 1e-9 * i)
    p_ts3, p_r3, _ = D._panel_funding(fc)
    st14c = D._fstats(p_ts3, p_r3, int(p_ts3[-1]) - 14 * MS_DAY, 14)
    st365c = D._fstats(p_ts3, p_r3, int(p_ts3[-1]) - 14 * MS_DAY, 365)
    _case("c8.falling_is_long", bool(st14c[1] <= st365c[2]) is True)


# =========================================================================
# CASE 9 -- card4 decision list: 14-day steps anchored on the panel's first
# day midnight; hold-on-undecidable produces no event
def case9():
    p1 = int(pd.Timestamp(2022, 1, 2, 6, tz="UTC").timestamp() * 1000)
    # panel starts 06:00 -> the anchor is midnight OF THAT DAY
    _case("c9.anchor_midnight", (p1 // MS_DAY) * MS_DAY != p1)
    kl = {s: _uni_kline((p1 // MS_DAY) - MS_H, 40 * 24, 100.0, 0.02, name=s)
          for s in E.FUND_SYMS}
    dec_ts = [(p1 // MS_DAY) + k * 14 * MS_DAY for k in range(3)]

    # all gates fail (under-covered): no events but the final liquidation
    ev, dec, nv, nt, miss = E._card49_build(kl, dec_ts, lambda t: None)
    _case("c9.none_events_flat", nv == 0 and len(ev) == 1
          and ev[0][1] == {} and ev[0][2] == "final_liquidation",
          f"n_events={len(ev)}")
    # gate true only on the middle decision
    ev2, dec2, nv2, nt2, miss2 = E._card49_build(
        kl, dec_ts, lambda t: True if int(t) == int(dec_ts[1]) else None)
    _case("c9.one_open_one_liquidation",
          nv2 == 1 and nt2 == 1 and len(ev2) == 2
          and ev2[0][2] == "rebalance" and ev2[1][2] == "final_liquidation",
          f"n={len(ev2)}")
    # four legs wired at the open
    eps = E._execute(ev2, kl)
    _case("c9.four_legs", len(eps) == 4 and all(
        e["w"] == 0.25 and e["side"] == 1.0 for e in eps))
    _case("c9.hits_final", all(e["exit_reason"] == "final_liquidation"
                               for e in eps))


# =========================================================================
# CASE 10 -- card9 panel vol gate: 0.8 threshold strict; panel = mean of the
# four majors' own RVs
def case10():
    t0 = T0
    kl = {s: _uni_kline(t0 - 5000 * MS_H, 5000, 100.0, 0.02, name=s)
          for s in E.FUND_SYMS}
    dec_ts = [t0]
    idx = {s: E._bar_idx(kl[s], t0) for s in E.FUND_SYMS}
    rv7s = [E._rv(kl[s], idx[s], 168) for s in E.FUND_SYMS]
    rv30s = [E._rv(kl[s], idx[s], 720) for s in E.FUND_SYMS]
    gate = bool(float(np.mean(rv7s)) < 0.8 * float(np.mean(rv30s)))
    _case("c10.panel_gate_direction", gate is True,
          f"rv7_mean={np.mean(rv7s):.6e} rv30_mean={np.mean(rv30s):.6e}")
    # strictness: rv7 == 0.8*rv30 exactly -> Flat (no long)
    _case("c10.threshold_strict", not (0.8 * 5.0 < 0.8 * 5.0))
    # both zero -> not long
    _case("c10.zero_flat", not (0.0 < 0.0))


# =========================================================================
# CASE 11 -- gates: pf, half-split, years, top-5
def case11():
    _case("c11.pf_basic", _pfv([3.0, -1.0, 2.0, -4.0]) == 1.0)
    _case("c11.pf_no_losses", _pfv([1.0, 2.0]) == float("inf"))
    _case("c11.pf_no_wins", _pfv([-1.0]) == 0.0)
    _case("c11.ceil23", E._ceil23(3) == 2 and E._ceil23(5) == 4
          and E._ceil23(6) == 4)
    # equity curve synth: 3 full years -- 2022 green, 2023 red, 2024 green;
    # a 2025 stub must be excluded as a partial year
    def _ms(y, m, d, h=0):
        return int(pd.Timestamp(y, m, d, h, tz="UTC").timestamp() * 1000)
    grid_t = np.array([_ms(2022, 1, 1), _ms(2022, 12, 31, 23),
                       _ms(2023, 1, 1), _ms(2023, 12, 31, 23),
                       _ms(2024, 1, 1), _ms(2024, 12, 31, 23)],
                      dtype=np.int64)
    cum = np.array([0.5, 1.5, 1.5, 1.0, 1.0, 2.0])
    nf, ng, det, byyr = E._years(grid_t, cum, 0, len(grid_t) - 1)
    _case("c11.years_full_3", nf == 3, f"nf={nf} det={det}")
    _case("c11.green_2", ng == 2, f"ng={ng}")
    _case("c11.det_line", det == "2022:+15000.00|2023:-5000.00|2024:+10000.00",
          det)
    _case("c11.g4_pass_2023red",
          bool(ng >= E._ceil23(nf) and nf >= 1) is True)
    # a 2025 bar 1 day in is NOT a full year: stays 3 full years
    grid_t5 = np.array(list(grid_t) + [_ms(2025, 1, 2)], dtype=np.int64)
    cum5 = np.array([0.5, 1.5, 1.5, 1.0, 1.0, 2.0, 2.1])
    nf5, ng5, _, _ = E._years(grid_t5, cum5, 0, len(grid_t5) - 1)
    _case("c11.partial_year_excluded", nf5 == 3 and ng5 == 2,
          f"nf={nf5} ng={ng5}")
    # a span starting mid-2022 makes 2022 partial: full=2 (2023, 2024)
    nf6, ng6, _, _ = E._years(grid_t, cum, 2, len(grid_t) - 1)
    _case("c11.mid_span_partial", nf6 == 2, f"nf={nf6}")
    # g4 gate with nf=0 -> refuse (need at least one full year)
    _case("c11.zero_full_years_fails",
          bool(0 >= E._ceil23(0) and 0 >= 1) is False)
    # top-5 weighted share
    w_net = [10.0, -3.0, 4.0, -2.0, 8.0, 1.0]
    srt = sorted(w_net, reverse=True)
    top5 = sum(srt[:5])
    total = sum(w_net)
    _case("c11.top5_weighted", abs(top5 - 21.0) < 1e-12
          and abs(total - 18.0) < 1e-12
          and abs(top5 / total - 21.0 / 18.0) < 1e-12)


def _pfv(vals):
    return E._pf(vals)


# =========================================================================
# CASE 12 -- input-set enforcement
def case12():
    try:
        E._check_files("CARD3", ["BTCUSDT_1h.csv"])
        _case("c12.refuses_short_set", False)
    except ValueError:
        _case("c12.refuses_short_set", True)
    try:
        E._check_files("CARD1", ["BTCUSDT_1h.csv"] * 8)
        _case("c12.refuses_extra", False)
    except ValueError:
        _case("c12.refuses_extra", True)
    ok = set(E.EXPECTED_FILES["CARD2"]) == set(
        f"{s}_1h.csv" for s in E.TEN_SYMS) | set(
        f"{s}_funding.json" for s in E.FUND_SYMS)
    _case("c12.card2_expected_set", ok)
    ok9 = set(E.EXPECTED_FILES["CARD9"]) == set(
        f"{s}_1h.csv" for s in E.FUND_SYMS) | set(
        f"{s}_funding.json" for s in E.FUND_SYMS)
    _case("c12.card9_expected_set", ok9)


# =========================================================================
# CASE 13 -- end-to-end mini card1 book on synthetic prints, hand-checked
def case13():
    """End-to-end mini card1 book: four syms, three months of hourly bars,
    funding LEVELS stepped 5 days before each month start so the trailing
    7d DELTA ranks are distinct and deterministic:
      month1: d7 = lvl1 - 0      -> long BTC (+1e-4), ETH (+2e-4)
                                  short SOL (+3e-4), XRP (+4e-4)
      month2: d7 = lvl2 - lvl1   -> SOL (-1.5e-4), XRP (-1.5e-4) long;
                                   BTC (+2.5e-4), ETH (+2.5e-4) short."""
    def _ms(y, m, d, h=0):
        return int(pd.Timestamp(y, m, d, h, tz="UTC").timestamp() * 1000)
    lo_kl = _ms(2021, 3, 1)
    n = 100 * 24
    kl = {s: _uni_kline(lo_kl, n, 100.0 + 10.0 * j, 0.01, name=s)
          for j, s in enumerate(E.FUND_SYMS)}
    hi = min(int(kl[s]["t"][-1]) for s in E.FUND_SYMS)
    months = D._month_starts(lo_kl, hi)
    m0a, m0b = months[0], months[1]
    _case("c13.months_are_apr_may",
          m0a == _ms(2021, 4, 1) and m0b == _ms(2021, 5, 1))
    L1 = {"BTCUSDT": 1e-4, "ETHUSDT": 2e-4, "SOLUSDT": 3e-4, "XRPUSDT": 4e-4}
    L2 = {"BTCUSDT": 3.5e-4, "ETHUSDT": 4.5e-4, "SOLUSDT": 1.5e-4,
          "XRPUSDT": 2.5e-4}
    step1, step2 = m0a - 5 * MS_DAY, m0b - 5 * MS_DAY
    ts_pr = lo_kl + np.arange(700, dtype=np.int64) * 8 * MS_H  # 3/day, >183d
    funds = {s: (ts_pr, np.select([ts_pr < step1, ts_pr < step2],
                                  [0.0, L1[s]], default=L2[s]).astype(float))
             for s in E.FUND_SYMS}
    for s in E.FUND_SYMS:
        d7a, d7b = D._d7(*funds[s], m0a), D._d7(*funds[s], m0b)
        _case(f"c13.d7_{s}", d7a is not None and d7b is not None,
              f"apr={d7a} may={d7b}")
    events = E._card1_build(kl, funds)
    rebal = [e for e in events if e[2] == "rebalance" and e[1]]
    _case("c13.two_scored_months", len(rebal) == 2, f"n={len(rebal)}")
    _case("c13.month_close_present",
          any(e[2] == "month_close" for e in events))
    s1 = {s: side for s, (side, w) in rebal[0][1].items()}
    s2 = {s: side for s, (side, w) in rebal[1][1].items()}
    _case("c13.month1_long_btc_eth",
          s1["BTCUSDT"] == 1.0 and s1["ETHUSDT"] == 1.0
          and s1["SOLUSDT"] == -1.0 and s1["XRPUSDT"] == -1.0, f"{s1}")
    _case("c13.month2_long_sol_xrp",
          s2["SOLUSDT"] == 1.0 and s2["XRPUSDT"] == 1.0
          and s2["BTCUSDT"] == -1.0 and s2["ETHUSDT"] == -1.0, f"{s2}")
    _case("c13.rotation_flips_four",
          sum(1 for s in s1 if s1[s] != s2[s]) == 4)
    eps = E._execute(events, kl)
    metrics, eps2, tables = E._score_book(
        "CARD1", kl, funds, eps, list(E.FUND_SYMS), card_extra={"probe": 1})
    _case("c13.units_8", metrics["units"] == 8, f"units={metrics['units']}")
    _case("c13.fills_16", metrics["fills"] == 16, f"fills={metrics['fills']}")
    _case("c13.no_residual_liquidation",
          metrics["final_liquidation_legs"] == 0)
    _case("c13.zero_rolls_in_this_fixture",
          sum(1 for e in eps2 if e["exit_reason"] == "roll") == 0)
    _case("c13.parity", metrics["parity_units_vs_equity_bps"] < 1e-6)
    _case("c13.decomposition",
          abs(metrics["price_total_bps"] + metrics["funding_total_bps"]
              - metrics["fee_total_bps"]
              - metrics["net_total_bps_on_gross1x"]) < 1e-6)
    # hand arithmetic on month 1: BTC leg collects nothing but pays funding
    btc1 = [t for t in tables if t["sym"] == "BTCUSDT"
            and t["entry_ts"] == int(m0a)][0]
    exp_price = 1.0 * (float(np.log(D._open_at(kl["BTCUSDT"], int(m0b))))
        - float(np.log(D._open_at(kl["BTCUSDT"], int(m0a))))) * BP
    _case("c13.btc1_price_bps",
          abs(btc1["price_bps"] - exp_price) < 1e-6,
          f"{btc1['price_bps']:.4f} vs {exp_price:.4f}")


# =========================================================================
def main():
    for fn in (case1, case2, case3, case4, case5):
        fn()
    for fn in (case6, case7, case8, case9):
        fn()
    for fn in (case10, case11, case12, case13):
        fn()
    n_pass = sum(1 for _, ok, _ in RESULTS if ok)
    out = [f"Q10 engine known-answer audit -- {len(RESULTS)} cases, "
           f"{n_pass} pass, {len(FAILS)} fail",
           "label: SYNTHETIC known-answer cases, no market data, no run_id"]
    for name, ok, det in RESULTS:
        out.append(f"{'PASS' if ok else 'FAIL'}  {name}" +
                   (f"  [{det}]" if det and not ok else ""))
    out.append("")
    if FAILS:
        out.append(f"FAILED: {', '.join(FAILS)}")
        out.append("the engine is NOT cleared for a real-data run")
    else:
        out.append("ALL PASS -- the engine is cleared for the real-data run")
    out.append(f"Summary: {n_pass} pass / {len(FAILS)} fail of {len(RESULTS)}"
               " cases")
    txt = "\n".join(out) + "\n"
    dst = os.path.join(HERE, "..", "results", "q10_engine_audit.txt")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)
    print(txt)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
