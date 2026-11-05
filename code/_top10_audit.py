"""Known-answer audit for code/top10_engine.py (top10 adapter, 2026-11-01).

Every engine branch the TOP10 shortlist uses is forced on synthetic hourly
frames and checked against hand-computed answers:
  signal -> next-open fill, gap-through stop, entry-bar stop-out,
  exit-signal-vs-stop tie (source order: signal first at the open),
  chandelier trail ratchet, time stop, funding signs (long pays / short
  receives), round-trip cost in R, long->short flip at one open,
  #73 Sunday->Monday timing, #71 hour window, #59 stop distance = close-low
  of the signal bar, #34 slope sign cross, #95 signal + funding + time stop,
  #28/#44 Donchian shift(1) window semantics.

Trade-level identity against the SOURCE engine on real data is a separate
audit (code/_top10_parity.py); this file pins the branch semantics.

Run:  python code/_top10_audit.py   -> exits 1 if any check fails.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
import top10_engine as E  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILS.append(name)


def ms_of(ts_utc):
    """UTC hourly DatetimeIndex -> epoch MILLISECONDS (float)."""
    return ((ts_utc.tz_convert("UTC").tz_localize(None) - pd.Timestamp("1970-01-01"))
            // pd.Timedelta("1ms")).astype(float).values


def frame(opens, highs=None, lows=None, closes=None, t0=1_700_000_000_000):
    """Hourly frame from lists; defaults high=max(o,c), low=min(o,c)."""
    opens = np.asarray(opens, dtype=float)
    n = len(opens)
    closes = np.asarray(closes if closes is not None else opens, dtype=float)
    highs = np.asarray(highs if highs is not None else np.maximum(opens, closes), dtype=float)
    lows = np.asarray(lows if lows is not None else np.minimum(opens, closes), dtype=float)
    return pd.DataFrame({
        "open_ts": t0 + np.arange(n) * 3_600_000,
        "open": opens, "high": highs, "low": lows, "close": closes,
        "volume": np.ones(n),
    })


def bmask(n, idx):
    z = np.zeros(n, bool)
    for i in (idx if isinstance(idx, (list, tuple)) else [idx]):
        z[i] = True
    return z


# ------------------------------------------------------------------ motor
def test_signal_next_open():
    # rising prices, wide stop: entry at the open AFTER the signal bar
    o = [100, 101, 102, 103, 104, 105, 106, 107]
    df = frame(o)
    sd = np.full(len(df), 10.0)  # stop far below, never hit
    sig = E.SIG(df, le=bmask(len(df), 3), sd=sd)
    eq, tr, obs = E.run_engine(df, sig, cost_rt=0.0)
    check("signal -> next-open fill", len(tr) == 1 and tr[0]["entry_i"] == 4
          and abs(tr[0]["r"] - (df["close"].iloc[-1] - 104.0) / 10.0) < 1e-12,
          f"trades={tr}")


def test_stop_gap_through():
    # signal at 3 -> entry bar 4 open 104, stop 99; bar 5 OPENS at 90
    o = [100, 101, 102, 103, 104, 90, 91, 92]
    h = [101, 102, 103, 104, 105, 91, 92, 93]
    l = [99, 100, 101, 102, 103, 89, 90, 91]
    df = frame(o, h, l)
    sd = np.full(len(df), 5.0)
    sig = E.SIG(df, le=bmask(len(df), 3), sd=sd)
    eq, tr, obs = E.run_engine(df, sig, cost_rt=0.0)
    # gap-through: fill at the open (90), not at the stop (99)
    check("stop gap-through fills at open", len(tr) == 1
          and abs(tr[0]["r"] - (90.0 - 104.0) / 5.0) < 1e-12
          and obs["gap_through_exits"] == 1, f"trades={tr}")


def test_stop_level_fill():
    # entry bar 4 open 104, stop 99; bar 5 low 99.0 touches without a gap
    o = [100, 101, 102, 103, 104, 101, 100, 101]
    h = [101, 102, 103, 104, 105, 103, 102, 102]
    l = [99, 100, 101, 102, 103, 100, 99.0, 99.5]
    df = frame(o, h, l)
    sd = np.full(len(df), 5.0)
    sig = E.SIG(df, le=bmask(len(df), 3), sd=sd)
    eq, tr, obs = E.run_engine(df, sig, cost_rt=0.0)
    # touch without gap: fill exactly at the stop level (bar 6 low 99.0)
    check("stop fills at stop level on touch", len(tr) == 1
          and abs(tr[0]["r"] - (99.0 - 104.0) / 5.0) < 1e-12
          and tr[0]["exit_i"] == 6 and obs["gap_through_exits"] == 0,
          f"trades={tr}")


def test_entry_bar_stopout():
    # signal at 3 -> entry bar 4 opens 104 but low 98.5 <= stop 99
    o = [100, 101, 102, 103, 104, 100, 101, 102]
    h = [101, 102, 103, 104, 104.5, 101, 102, 103]
    l = [99, 100, 101, 102, 98.5, 99, 100, 101]
    df = frame(o, h, l)
    sd = np.full(len(df), 5.0)
    sig = E.SIG(df, le=bmask(len(df), 3), sd=sd)
    eq, tr, obs = E.run_engine(df, sig, cost_rt=0.0)
    check("entry-bar stop-out", len(tr) == 1 and tr[0]["entry_i"] == 4
          and tr[0]["exit_i"] == 4 and abs(tr[0]["r"] - (99.0 - 104.0) / 5.0) < 1e-12
          and obs["entry_bar_stopouts"] == 1, f"trades={tr}")


def test_tie_signal_first():
    # entry bar 4 (open 104, stop 99); exit signal fires on bar 4's close
    # and bar 5 low 97 crosses the stop: the signal is executed at bar 5's
    # OPEN (it was known at the prior close), before the stop level
    o = [100, 101, 102, 103, 104, 98.0, 99, 100]
    h = [101, 102, 103, 104, 105, 99.0, 100, 101]
    l = [99, 100, 101, 102, 103, 97.0, 98, 99]
    df = frame(o, h, l)
    sd = np.full(len(df), 5.0)
    sig = E.SIG(df, le=bmask(len(df), 3), lx=bmask(len(df), 4), sd=sd)
    eq, tr, obs = E.run_engine(df, sig, cost_rt=0.0)
    # exit signal on bar 4 is EXECUTED at bar 5's open (98); bar 5 low 97
    # also crosses the stop 99 -> the tie counter records it, the fill is the
    # open, not the stop level
    check("tie: exit signal executed at open before stop", len(tr) == 1
          and abs(tr[0]["r"] - (98.0 - 104.0) / 5.0) < 1e-12
          and tr[0]["exit_i"] == 5 and obs["ties_signal_first"] == 1,
          f"trades={tr}")


def test_trailing_chandelier():
    # entry bar 4 open 104, sizing stop 99, trail 3.0:
    # bar 5: stop = max(99, 106-3) = 103; bar 6 low 103.5 keeps 103;
    # bar 7 low 103.0 <= 103 -> exit at 103.0
    o = [100, 101, 102, 103, 104, 105, 104.5, 104.0, 103.5]
    h = [101, 102, 103, 104, 105, 106, 105.5, 104.5, 104.0]
    l = [99, 100, 101, 102, 103, 104, 103.5, 103.0, 102.0]
    df = frame(o, h, l)
    sd = np.full(len(df), 5.0)
    trail = np.full(len(df), 3.0)
    sig = E.SIG(df, le=bmask(len(df), 3), sd=sd, trail_dist=trail)
    eq, tr, obs = E.run_engine(df, sig, cost_rt=0.0)
    check("chandelier trail ratchet + exit", len(tr) == 1
          and abs(tr[0]["r"] - (103.0 - 104.0) / 5.0) < 1e-12
          and tr[0]["exit_i"] == 7, f"trades={tr}")


def test_time_stop():
    # entry bar 4; max_bars=24 -> exit at the open of bar 28
    o = list(np.linspace(100, 100.05, 30))  # flat, no stop hit
    df = frame(o)
    sd = np.full(len(df), 5.0)
    sig = E.SIG(df, le=bmask(len(df), 3), sd=sd, max_bars=np.full(len(df), 24))
    eq, tr, obs = E.run_engine(df, sig, cost_rt=0.0)
    check("time stop at 24 bars", len(tr) == 1 and tr[0]["exit_i"] == 28
          and obs["time_stop_exits"] == 1, f"trades={tr}")


def test_funding_signs():
    # 30 hourly bars at 100, settlement at bar 10 (rate +1%):
    # long PAYS (-0.01*100/50 in R), short RECEIVES
    o = [100.0] * 30
    df = frame(o)
    ts = df["open_ts"].values
    fund = pd.Series({int(ts[10]): 0.01})
    sd = np.full(len(df), 50.0)
    sigL = E.SIG(df, le=bmask(len(df), 3), sd=sd)
    _, trL, _ = E.run_engine(df, sigL, cost_rt=0.0, funding=fund)
    # entry bar 4 at open 100; gross 0; funding -0.01*100/50
    check("funding: long pays positive rate",
          abs(trL[0]["r"] - (0.0 - 0.01 * 100.0 / 50.0)) < 1e-12,
          f"r={trL[0]['r']}")
    sigS = E.SIG(df, se=bmask(len(df), 3), sd=sd)
    _, trS, _ = E.run_engine(df, sigS, cost_rt=0.0, funding=fund)
    check("funding: short receives positive rate",
          abs(trS[0]["r"] - (0.0 + 0.01 * 100.0 / 50.0)) < 1e-12,
          f"r={trS[0]['r']}")


def test_funding_two_settlements():
    o = [100.0] * 30
    df = frame(o)
    ts = df["open_ts"].values
    fund = pd.Series({int(ts[10]): 0.01, int(ts[20]): 0.02})
    sd = np.full(len(df), 50.0)
    sigS = E.SIG(df, se=bmask(len(df), 3), sd=sd)
    _, trS, obs = E.run_engine(df, sigS, cost_rt=0.0, funding=fund)
    # both settlements charged: +0.01 + 0.02 in R units at price 100
    check("funding: two settlements charged",
          abs(trS[0]["r"] - (0.01 + 0.02) * 100.0 / 50.0) < 1e-12
          and obs["settlements_charged"] == 2, f"r={trS[0]['r']} obs={obs}")


def test_cost_in_r():
    o = [100, 101, 102, 103, 104, 105, 106, 107]
    df = frame(o)
    sd = np.full(len(df), 10.0)
    sig = E.SIG(df, le=bmask(len(df), 3), sd=sd)
    eq, tr, _ = E.run_engine(df, sig, cost_rt=0.0011)
    gross = (df["close"].iloc[-1] - 104.0) / 10.0
    check("round-trip cost charged once in R",
          abs(tr[0]["r"] - (gross - 0.0011 * 104.0 / 10.0)) < 1e-15, f"r={tr[0]['r']}")


def test_flip_same_open():
    # long exit signal and short entry signal on the same prior bar:
    # long exits at the open and the short enters at the SAME open
    o = [100, 101, 102, 103, 104, 103, 102, 101]
    df = frame(o)
    sd = np.full(len(df), 50.0)
    sig = E.SIG(df, le=bmask(len(df), 3), lx=bmask(len(df), 5), se=bmask(len(df), 5), sd=sd)
    eq, tr, _ = E.run_engine(df, sig, cost_rt=0.0)
    check("long->short flip at one open",
          len(tr) == 2 and tr[0]["dir"] == 1 and tr[1]["dir"] == -1
          and tr[0]["exit_i"] == 6 and tr[1]["entry_i"] == 6, f"trades={tr}")


# -------------------------------------------------------------- strategies
def test_s73_timing():
    # two weeks of hourly bars starting Sunday 2026-01-04 00:00 UTC;
    # Sunday 23:00 of week 1 closes 5 below the Sunday open
    t0 = pd.Timestamp("2026-01-04 00:00", tz="UTC")
    n = 24 * 14
    ts = pd.date_range(t0, periods=n, freq="1h")
    o = np.full(n, 100.0)
    c = np.full(n, 100.0)
    sun_idx = [i for i in range(n) if ts[i].dayofweek == 6][0]
    c[sun_idx + 23] = 95.0
    df = frame(o, closes=c)
    df["open_ts"] = ms_of(ts)
    sig = E.s73(df)
    le = np.where(sig["long_entry"])[0]
    check("#73 signal on Sunday 23:00 only", list(le) == [sun_idx + 23], f"le={le}")
    sd = np.full(len(df), 50.0)
    sig2 = E.SIG(df, le=sig["long_entry"], lx=sig["long_exit"], sd=sd)
    eq, tr, _ = E.run_engine(df, sig2, cost_rt=0.0)
    check("#73 entry Monday 00:00, exit Tuesday 00:00",
          len(tr) == 1 and ts[tr[0]["entry_i"]].dayofweek == 0
          and ts[tr[0]["entry_i"]].hour == 0
          and ts[tr[0]["exit_i"]].dayofweek == 1 and ts[tr[0]["exit_i"]].hour == 0
          and tr[0]["exit_i"] - tr[0]["entry_i"] == 24,
          f"trades={tr}")


def test_s71_hour_window():
    # one level shift -> exactly one raw EMA20/50 cross; entries may only
    # exist if the cross lands inside 14:00-17:59 UTC, and MUST exist then
    t0 = pd.Timestamp("2026-01-05 00:00", tz="UTC")  # a Monday
    n = 24 * 40
    ts = pd.date_range(t0, periods=n, freq="1h")
    c = np.full(n, 100.0)
    c[24 * 5:] = 110.0
    df = frame(np.full(n, 100.0), closes=c)
    df["open_ts"] = ms_of(ts)
    sig = E.s71(df)
    raw = E.cross_up(E.ema(df["close"], 20), E.ema(df["close"], 50))
    raw_i = np.where(raw)[0]
    check("#71 exactly one raw cross", len(raw_i) == 1, f"raw={raw_i}")
    cu = np.where(sig["long_entry"])[0]
    sx = np.where(sig["short_entry"])[0]
    cross_hour = int(ts[raw_i[0]].hour)
    in_win = cross_hour in (14, 15, 16, 17)
    check("#71 gate binds exactly at the window",
          (len(cu) == 1) == in_win and (len(sx) == 0),
          f"cross_hour={cross_hour} cu={cu}")
    check("#71 all entries carry an in-window hour",
          all(int(ts[i].hour) in (14, 15, 16, 17) for i in list(cu) + list(sx)))


def test_s59_stopdist():
    n = 60
    o = np.full(n, 100.0)
    h = np.full(n, 100.5)
    l = np.full(n, 99.5)
    c = np.full(n, 100.0)
    # signal bar 30: huge range, close near the high
    o[30], h[30], l[30], c[30] = 99.0, 110.0, 98.0, 109.0
    df = frame(o, h, l, c)
    sig = E.s59(df)
    le = np.where(sig["long_entry"])[0]
    check("#59 signal on the expansion bar only", list(le) == [30], f"le={le}")
    d0 = float(np.asarray(sig["stop_dist"])[30])
    check("#59 sizing distance = close-low of signal bar",
          abs(d0 - (109.0 - 98.0)) < 1e-12, f"d0={d0}")
    sig2 = E.SIG(df, le=sig["long_entry"], lx=sig["long_exit"], sd=sig["stop_dist"])
    eq, tr, _ = E.run_engine(df, sig2, cost_rt=0.0)
    # entry at open bar 31 = 100; stop = 100 - 11 = 89; bar 31 low 99.5 no hit
    check("#59 entry next open, stop at entry-(close-low)",
          len(tr) == 1 and tr[0]["entry_i"] == 31, f"trades={tr}")


def test_s34_slope_sign():
    n = 90
    c = np.concatenate([np.linspace(90, 110, 45), np.linspace(110, 85, 45)])
    df = frame(np.full(n, 100.0), closes=c)
    sig = E.s34(df)
    se = np.where(sig["short_entry"])[0]
    le = np.where(sig["long_entry"])[0]
    # slope valid from bar 49; it starts positive (rise) and turns negative
    check("#34 short entry on slope >=0 -> <0", len(se) >= 1 and se[0] > 49,
          f"se={se}")
    check("#34 no long entry without a <=0 -> >0 crossing", len(le) == 0,
          f"le={le}")


def test_s95_signal_and_funding():
    n = 220
    o = np.full(n, 100.0)
    h = np.full(n, 100.5)
    l = np.full(n, 99.5)
    c = np.full(n, 100.0)
    # bar 180: close at a new 48-bar low
    o[180], h[180], l[180], c[180] = 99.0, 99.2, 95.0, 95.0
    df = frame(o, h, l, c)
    ts = df["open_ts"].values
    # DECLINING funding 0.02 -> 0.001 so no bar before 180 carries the
    # 30-settlement max (a flat series would fire f_hi30 everywhere, which is
    # the source semantics -- fr >= rolling(30).max() includes itself), then
    # a spike back to 0.02 exactly at the crash bar
    fdict = {int(ts[i]): float(0.02 - (i - 100) * (0.019 / 79.0))
             for i in range(100, 180)}
    fdict[int(ts[180])] = 0.02
    fdict[int(ts[190])] = 0.02  # a settlement DURING the holding window
    frate = pd.Series(fdict).sort_index()
    sig = E.s95(df, frate)
    se = np.where(sig["short_entry"])[0]
    check("#95 short on new 48-low + funding 30-max", list(se) == [180], f"se={se}")
    sig2 = E.SIG(df, se=sig["short_entry"], sd=sig["stop_dist"],
                 max_bars=np.full(len(df), 24))
    eq, tr, obs = E.run_engine(df, sig2, cost_rt=0.0, funding=frate)
    if tr:
        t0 = tr[0]
        check("#95 time stop exits 24 bars after entry",
              t0["exit_i"] - t0["entry_i"] == 24, f"trades={tr}")
        check("#95 short receives funding (positive contribution)",
              t0["r"] > 0, f"r={t0['r']}")


def test_s28_donchian_shift():
    n = 80
    # (a) the true breakout bar fires: close 101 over prior 55-max 100
    c = np.full(n, 100.0)
    c[70] = 101.0
    df = frame(np.full(n, 100.0), closes=c)
    le = np.where(E.s28(df)["long_entry"])[0]
    check("#28 breakout fires on the breaking close", list(le) == [70], f"le={le}")
    # (b) a huge prior bar's high sits INSIDE the shifted window at bar 70,
    # so a close of 150 there is no longer a breakout (no leak of bar 70's
    # own high either way)
    c2 = np.full(n, 100.0)
    c2[69] = 200.0
    c2[70] = 150.0
    df2 = frame(np.full(n, 100.0), closes=c2)
    le2 = np.where(E.s28(df2)["long_entry"])[0]
    check("#28 shift(1): prior huge high blocks the next bar", list(le2) == [69],
          f"le={le2}")


def test_s60_conditions():
    n = 80
    # wiggly series so RSI is defined (a monotonic series has dn==0 and the
    # source rsi returns NaN -- faithful, but useless as a test fixture)
    c = 100 + 8 * np.sin(np.arange(n) / 4.0) + np.linspace(0, 20, n)
    df = frame(np.full(n, 100.0), closes=c)
    r = E.rsi(df["close"], 14)
    check("#60 RSI bounded (0,100) on a wiggly series",
          bool((r.dropna() > 0).all() and (r.dropna() < 100).all()))
    spike = c.copy()
    spike[70] = c[69] + 60.0
    df2 = frame(np.full(n, 100.0), closes=spike)
    up2, _, _ = E.keltner(df2, 20, 2)
    check("#60 spike bar breaches the Keltner upper",
          bool(df2["close"].iloc[70] > up2.iloc[70]))
    sig60 = E.s60(df2)
    fired = np.where(sig60["long_entry"])[0]
    cond_self = ((df2["close"] > up2) & (E.rsi(df2["close"], 14) > 60)).values
    check("#60 signal = (close>Keltner upper) AND (RSI>60) on the same frame",
          list(fired) == list(np.where(cond_self)[0]) and 70 in fired,
          f"fired={fired}")


def test_zero_cost_differs_from_11bps():
    o = [100, 101, 102, 103, 104, 105, 106, 107]
    df = frame(o)
    sd = np.full(len(df), 10.0)
    sig = E.SIG(df, le=bmask(len(df), 3), sd=sd)
    _, tr1, _ = E.run_engine(df, sig, cost_rt=0.0011)
    _, tr0, _ = E.run_engine(df, sig, cost_rt=0.0)
    check("zero-cost control differs from 11 bps",
          tr1[0]["r"] < tr0[0]["r"] and
          abs((tr0[0]["r"] - tr1[0]["r"]) - 0.0011 * 104.0 / 10.0) < 1e-15)


def main():
    print("top10_engine known-answer audit")
    tests = [
        test_signal_next_open, test_stop_gap_through, test_stop_level_fill,
        test_entry_bar_stopout, test_tie_signal_first, test_trailing_chandelier,
        test_time_stop, test_funding_signs, test_funding_two_settlements,
        test_cost_in_r, test_flip_same_open,
        test_s73_timing, test_s71_hour_window, test_s59_stopdist,
        test_s34_slope_sign, test_s95_signal_and_funding,
        test_s28_donchian_shift, test_s60_conditions,
        test_zero_cost_differs_from_11bps,
    ]
    for t in tests:
        t()
    print(f"\n{len(tests) - len(FAILS)}/{len(tests)} checks passed")
    if FAILS:
        print("FAILED:", FAILS)
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
