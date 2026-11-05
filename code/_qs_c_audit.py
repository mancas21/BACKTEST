#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_qs_c_audit.py — known-answer audit for family C (QS-021..QS-030).
Run BEFORE any campaign artifact; the report cites this file's output."""
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import qs_c_strats as C       # noqa: E402  (registers into qs_strats.SPECS)
import qs_strats as SD        # noqa: E402
import qs_engine as E         # noqa: E402

RESULTS = os.path.join(ROOT, "results", "qs_c_audit_known_answers.txt")
OUT = []
FAILED = []
HOUR = 3600_000
M15 = 15 * 60_000
T0 = 1700000000000 - (1700000000000 % 86400000)   # a UTC midnight


def check(name, ok, detail=""):
    line = f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else "")
    OUT.append(line)
    print(line, flush=True)
    if not ok:
        FAILED.append(name)


def close(a, b, tol=1e-9):
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def ev(plan, key):
    return np.asarray(pd.Series(plan[key]).fillna(False), bool)


def bars(closes, volumes=None, tf_ms=HOUR, t_start=None):
    n = len(closes)
    c = np.asarray(closes, float)
    v = np.full(n, 100.0) if volumes is None else np.asarray(volumes, float)
    o = np.roll(c, 1); o[0] = c[0]
    h = np.maximum(o, c) + 0.1
    l = np.minimum(o, c) - 0.1
    base = T0 if t_start is None else t_start
    t = np.array([base + i * tf_ms for i in range(n)], np.int64)
    return pd.DataFrame(dict(open_ts=t, open=o, high=h, low=l, close=c,
                             volume=v, ts=pd.to_datetime(t, unit="ms", utc=True)))


def c_audit():
    # ── C1 QS-021: wide calm 101 (ATR100 warmup) → tight 20 (the Wilder ATR
    # decay needs ~8 tight bars before the ratio is stably < 0.7 for 10
    # consecutive bars) → expansion bar closing in the top 30% of its range.
    calm_c = np.where(np.arange(100) % 2 == 0, 100.5, 99.5)
    closes = np.concatenate([calm_c, [100.0], np.full(20, 100.0), [101.4]])
    df = bars(closes)
    o = df["open"].to_numpy(float).copy()
    h = df["high"].to_numpy(float).copy()
    l = df["low"].to_numpy(float).copy()
    for i in range(101):
        o[i], h[i], l[i] = (100.0 if i % 2 else 99.5), 100.6, 99.4
    for i in range(101, 121):
        o[i], h[i], l[i] = 100.0, 100.1, 99.9
    o[121], h[121], l[121] = 100.0, 101.6, 99.4
    df["open"], df["high"], df["low"] = o, h, l
    p = SD.SPECS["QS-021"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("C1a QS-021 long fires on the expansion bar after compression",
          int(e.sum()) == 1 and bool(e[121]),
          f"events at {list(np.flatnonzero(e))}")
    # mirror: a down expansion closing in the BOTTOM 30% fires the short
    closes2 = np.concatenate([calm_c, [100.0], np.full(20, 100.0), [98.6]])
    df2 = bars(closes2)
    o2 = df2["open"].to_numpy(float).copy()
    h2 = df2["high"].to_numpy(float).copy()
    l2 = df2["low"].to_numpy(float).copy()
    for i in range(101):
        o2[i], h2[i], l2[i] = (100.0 if i % 2 else 99.5), 100.6, 99.4
    for i in range(101, 121):
        o2[i], h2[i], l2[i] = 100.0, 100.1, 99.9
    o2[121], h2[121], l2[121] = 100.0, 100.6, 98.4
    df2["open"], df2["high"], df2["low"] = o2, h2, l2
    p2 = SD.SPECS["QS-021"]["build"](df2, "1h")
    e2 = ev(p2, "short_event")
    check("C1b QS-021 short fires on the down expansion bar",
          int(e2.sum()) == 1 and bool(e2[121]))

    # ── C2 QS-022: noisy history → vol collapse into the lowest decile of
    # bandwidth → close above the upper band.
    rng = np.random.default_rng(5)
    hist = 100 + rng.normal(0, 0.05, 240)
    quiet = np.full(8, 100.0)
    closes = np.concatenate([hist, quiet, [100.6]])     # breakout bar
    df = bars(closes)
    p = SD.SPECS["QS-022"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("C2 QS-022 long fires on the band break after the squeeze",
          int(e.sum()) == 1 and bool(e[248]),
          f"events at {list(np.flatnonzero(e))}")

    # ── C3 QS-023: vol collapse (pct < 40) then expansion (pct crosses 60)
    # with the close exceeding the prior 30-bar high. The rise must carry
    # NOISY returns (a linear ramp has almost no 48-bar variance) and be
    # steep enough for rv(48) to rank above the noisy history's 60th pct.
    noisy = 100 + np.cumsum(rng.normal(0, 0.25, 620))
    quiet = 100 + np.cumsum(rng.normal(0, 0.02, 60))
    rise = 100 + np.cumsum(rng.normal(0.7, 0.4, 40))
    closes = np.concatenate([noisy, quiet, rise])
    df = bars(closes)
    p = SD.SPECS["QS-023"]["build"](df, "1h")
    e = ev(p, "long_event")
    idxs = list(np.flatnonzero(e))
    check("C3 QS-023 long fires after the vol-regime cross + 30-bar-high break",
          any(680 <= i <= 719 for i in idxs),
          f"events tail {idxs[-3:] if idxs else []}")

    # ── C4 QS-024 opening range (UTC 00:00 anchor), explicit 15m bars.
    # Day 1: OR bars 00:00/00:15 with high 101/102 (OR high 102), low
    # 100/100.5 (OR low 100). 00:30 close 101 (no event), 00:45 close 102.5
    # (event, stop = OR low 100).
    rows = []
    def m15(day_off, hh, mm, oo, hh_, ll, cc):
        t = T0 + day_off * 86_400_000 + (hh * 60 + mm) * 60_000
        rows.append((t, oo, hh_, ll, cc))
    m15(0, 0, 0, 100.0, 101.0, 100.0, 100.8)
    m15(0, 0, 15, 100.8, 102.0, 100.5, 101.5)
    m15(0, 0, 30, 101.5, 101.8, 101.2, 101.0)     # above OR? no (102)
    m15(0, 0, 45, 101.0, 102.7, 100.9, 102.5)     # breakout -> event
    m15(0, 1, 0, 102.5, 103.0, 102.2, 102.6)      # stays above; no new edge
    m15(1, 0, 0, 102.0, 103.5, 101.8, 103.0)      # day 2 OR
    m15(1, 0, 15, 103.0, 104.0, 102.9, 103.8)
    m15(1, 0, 30, 103.8, 104.2, 103.6, 104.5)     # day-2 breakout (OR hi 104)
    t = np.array([r[0] for r in rows], np.int64)
    df = pd.DataFrame(dict(open_ts=t, open=[r[1] for r in rows],
                           high=[r[2] for r in rows], low=[r[3] for r in rows],
                           close=[r[4] for r in rows],
                           volume=np.full(len(rows), 100.0),
                           ts=pd.to_datetime(t, unit="ms", utc=True)))
    p = SD.SPECS["QS-024"]["build"](df, "15m")
    e = ev(p, "long_event")
    stop_l = pd.Series(p["stop_level_long"])
    # day-2 OR low = min(101.8, 102.9) = 101.8
    check("C4a QS-024 long events exactly at the two OR breakouts",
          list(np.flatnonzero(e)) == [3, 7],
          f"events at {list(np.flatnonzero(e))}")
    check("C4b QS-024 stop level = the OR low of the signal day",
          close(stop_l.iloc[3], 100.0, 1e-9) and close(stop_l.iloc[7], 101.8, 1e-9),
          f"stops at events {[round(float(stop_l.iloc[i]), 3) for i in (3, 7)]}")

    # ── C5 QS-025 volume confirmation: same breakout with and without
    # volume. The quiet baseline (100) makes the 20-bar SMA ~105, so the
    # 2x threshold is ~210: a 250-volume breakout fires, a 150 one does not.
    base = np.full(30, 100.0)
    bo = [103.0]
    vols = np.full(31, 100.0)
    df = bars(np.concatenate([base, bo]), volumes=vols)
    v = df["volume"].astype(float).copy()
    v[30] = 250.0
    df["volume"] = v
    p = SD.SPECS["QS-025"]["build"](df, "1h")
    ok_v = int(ev(p, "long_event").sum()) == 1 and bool(ev(p, "long_event")[30])
    vols2 = np.full(31, 100.0)
    df2 = bars(np.concatenate([base, bo]), volumes=vols2)
    v2 = df2["volume"].astype(float).copy()
    v2[30] = 150.0
    df2["volume"] = v2
    p2 = SD.SPECS["QS-025"]["build"](df2, "1h")
    ok_novol = int(ev(p2, "long_event").sum()) == 0
    check("C5 QS-025 breakout fires with 2x volume, stays silent without",
          ok_v and ok_novol)

    # ── C6 QS-026 NR7: quiet base range 2.0, NR bar range 0.4, first close
    # above the NR high fires within 3 bars; the 4th bar does not.
    base = [100.0] * 12
    nr_bar = [100.0]
    closes = np.concatenate([base, nr_bar, [102.0]])
    df = bars(closes)
    o = df["open"].to_numpy(float).copy(); h = df["high"].to_numpy(float).copy()
    l = df["low"].to_numpy(float).copy()
    o[-1], h[-1], l[-1] = 101.0, 102.5, 101.0      # range 1.5 < 2.1 base
    o[-2], h[-2], l[-2] = 100.0, 100.3, 99.9       # NR bar: range 0.4
    for i in range(12):
        o[i], h[i], l[i] = 100.0, 101.0, 99.0      # base range 2.0
    df["open"], df["high"], df["low"] = o, h, l
    p = SD.SPECS["QS-026"]["build"](df, "1h")
    e = ev(p, "long_event")
    tp = float(pd.Series(p["tp_dist_long"]).dropna().iloc[0])
    dist = float(pd.Series(p["stop_dist_long"]).dropna().iloc[0])
    check("C6a QS-026 long fires on the first close above the NR7 high",
          int(e.sum()) == 1 and bool(e[13]),
          f"events at {list(np.flatnonzero(e))}")
    check("C6b QS-026 NR7 stop below the NR low and TP = 2R",
          close(dist, 102.0 - 99.9, 1e-9) and close(tp, 2.0 * dist, 1e-9),
          f"dist={dist:.3f} tp={tp:.3f}")
    # window boundary: close above arrives on the 4th bar -> no event
    closes2 = np.concatenate([base, nr_bar, [99.0], [99.0], [99.0], [102.0]])
    df2 = bars(closes2)
    o2 = df2["open"].to_numpy(float).copy(); h2 = df2["high"].to_numpy(float).copy()
    l2 = df2["low"].to_numpy(float).copy()
    o2[-4], h2[-4], l2[-4] = 100.0, 100.3, 99.9
    for i in (13, 14, 15):
        o2[i], h2[i], l2[i] = 99.0, 99.2, 98.8
    o2[16], h2[16], l2[16] = 99.0, 102.5, 98.9
    df2["open"], df2["high"], df2["low"] = o2, h2, l2
    p2 = SD.SPECS["QS-026"]["build"](df2, "1h")
    check("C6c QS-026 close above the NR high on the 4th bar does not fire",
          int(ev(p2, "long_event").sum()) == 0)

    # ── C7 QS-027 chandelier flips: downtrend then a close above
    # ll22 + 3*ATR fires the long; uptrend then close below hh22 - 3*ATR
    # fires the short; the plan carries the native trailing multiplier.
    dn = np.linspace(120, 90, 40)
    closes = np.concatenate([dn, [96.0]])
    df = bars(closes)
    p = SD.SPECS["QS-027"]["build"](df, "1h")
    e_l = ev(p, "long_event")
    ok_long = len(e_l) > 0 and bool(e_l[40])
    ok_trail = float(p["trailing_atr_mult"]) == 3.0
    up = np.linspace(80, 120, 40)
    closes2 = np.concatenate([up, [115.0]])
    p2 = SD.SPECS["QS-027"]["build"](bars(closes2), "1h")
    e_s = ev(p2, "short_event")
    check("C7 QS-027 chandelier flip fires both sides + native trailing stop",
          ok_long and ok_trail and len(e_s) > 0 and bool(e_s[40]))

    # ── C8 QS-028 failed breakout: the broken level is the 20-bar low
    # (98.0); the breakdown (close 97.5, extreme low 97.0) recovers with a
    # close back above 98.0; a recovery arriving on the 4th bar does not
    # fire. TP = the 20-bar range midpoint at the breakdown (99.1).
    base = np.full(30, 99.0)
    closes = np.concatenate([base, [97.5], [98.5]])
    df = bars(closes)
    o = df["open"].to_numpy(float).copy(); h = df["high"].to_numpy(float).copy()
    l = df["low"].to_numpy(float).copy()
    for i in range(30):
        o[i], h[i], l[i] = 99.0, 100.2, 98.0
    o[30], h[30], l[30] = 98.5, 98.6, 97.0
    o[31], h[31], l[31] = 98.0, 98.9, 97.9
    df["open"], df["high"], df["low"] = o, h, l
    p = SD.SPECS["QS-028"]["build"](df, "1h")
    e = ev(p, "long_event")
    tp = float(pd.Series(p["tp_dist_long"]).dropna().iloc[0])
    check("C8a QS-028 long fires on the first close back above the broken low",
          int(e.sum()) == 1 and bool(e[31]),
          f"events at {list(np.flatnonzero(e))}")
    check("C8b QS-028 target = the range midpoint measured at the breakdown",
          close(tp, 99.1 - 98.5, 1e-6), f"tp={tp:.3f}")
    closes2 = np.concatenate([base, [97.5], [97.5], [97.5], [97.5], [98.5]])
    df2 = bars(closes2)
    o2 = df2["open"].to_numpy(float).copy(); h2 = df2["high"].to_numpy(float).copy()
    l2 = df2["low"].to_numpy(float).copy()
    for i in range(30):
        o2[i], h2[i], l2[i] = 99.0, 100.2, 98.0
    o2[30], h2[30], l2[30] = 98.5, 98.6, 97.0
    for i in (31, 32, 33):
        o2[i], h2[i], l2[i] = 97.6, 97.9, 97.3   # below the broken 98.0 level,
        # above the post-breakdown 20-bar low (97.0): no recovery, no reset
    o2[34], h2[34], l2[34] = 98.3, 98.9, 98.2
    df2["open"], df2["high"], df2["low"] = o2, h2, l2
    p2 = SD.SPECS["QS-028"]["build"](df2, "1h")
    check("C8c QS-028 recovery on the 4th bar does not fire",
          int(ev(p2, "long_event").sum()) == 0)

    # ── C9 QS-029 breakout then retest within 0.25*ATR of L, then a bar
    # closing above L and above its open.
    base = np.full(30, 100.0)
    closes = np.concatenate([base, [104.0], [102.0], [102.5]])
    df = bars(closes)
    o = df["open"].to_numpy(float).copy(); h = df["high"].to_numpy(float).copy()
    l = df["low"].to_numpy(float).copy()
    o[30], h[30], l[30] = 100.5, 104.5, 100.2      # breakout bar (L=100.1)
    o[31], h[31], l[31] = 103.0, 103.2, 100.3      # retest touch (low <= L+0.25a)
    o[32], h[32], l[32] = 101.0, 102.8, 100.9      # close > L and > open
    df["open"], df["high"], df["low"] = o, h, l
    p = SD.SPECS["QS-029"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("C9a QS-029 long fires on the confirmed retest bar",
          int(e.sum()) == 1 and bool(e[32]),
          f"events at {list(np.flatnonzero(e))}")
    lvl = float(pd.Series(p["stop_level_long"]).dropna().iloc[0])
    a32 = float(p["atr"].iloc[32])
    dist = min(102.5 - (100.1 - 0.75 * a32), 3.0 * a32)   # the 3*ATR cap
    check("C9b QS-029 stop = L minus 0.75*ATR (3*ATR distance cap applied)",
          close(lvl, 102.5 - dist, 1e-6),
          f"stop={lvl:.3f} expected={102.5 - dist:.3f}")
    # a retest bar closing BELOW its open does not confirm
    closes2 = np.concatenate([base, [104.0], [102.0], [102.5]])
    df2 = bars(closes2)
    o2 = df2["open"].to_numpy(float).copy(); h2 = df2["high"].to_numpy(float).copy()
    l2 = df2["low"].to_numpy(float).copy()
    o2[30], h2[30], l2[30] = 100.5, 104.5, 100.2
    o2[31], h2[31], l2[31] = 103.0, 103.2, 100.3
    o2[32], h2[32], l2[32] = 103.0, 103.1, 100.9   # close 102.5 < open 103
    df2["open"], df2["high"], df2["low"] = o2, h2, l2
    p2 = SD.SPECS["QS-029"]["build"](df2, "1h")
    check("C9c QS-029 retest bar closing below its open does not fire",
          int(ev(p2, "long_event").sum()) == 0)

    # ── C10 QS-030 HTF regime: a 1h uptrend (4h regime up) lets longs
    # through; after the trend rolls over the short side opens.
    up = 100 + np.linspace(0, 40, 500)
    over = 140 + np.linspace(0, 4, 40)
    dn = 144 - np.linspace(0, 50, 300)
    closes = np.concatenate([up, over, dn])
    df = bars(closes)
    p = SD.SPECS["QS-030"]["build"](df, "1h")
    e_l, e_s = ev(p, "long_event"), ev(p, "short_event")
    check("C10a QS-030 longs fire inside the HTF uptrend",
          int(e_l.sum()) > 0 and bool(e_l[:560].any()))
    check("C10b QS-030 shorts fire after the HTF regime rolls over",
          int(e_s.sum()) > 0 and bool(e_s[560:].any()))
    check("C10c QS-030 no shorts inside the HTF uptrend",
          int(e_s[:500].sum()) == 0)


def real_audit():
    path = "data/binance_klines_1h_taker/BTCUSDT_1h.csv"
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df["ts"] = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
    df = df.sort_values("ts").reset_index(drop=True)
    plan_fn = SD.SPECS["QS-025"]["build"]
    cut = int(len(df) * 0.6)
    p1 = plan_fn(df, "1h")
    p2 = plan_fn(df.iloc[:cut].reset_index(drop=True), "1h")
    ok = all(np.array_equal(
        np.asarray(pd.Series(p1[k]).fillna(False), bool)[:cut],
        np.asarray(pd.Series(p2[k]).fillna(False), bool))
        for k in ("long_event", "short_event"))
    check("R1 truncation causality (QS-025 on real data)", ok)
    # QS-030's HTF map must also be causal: truncated frames agree bar-by-bar
    plan_fn30 = SD.SPECS["QS-030"]["build"]
    q1 = plan_fn30(df, "1h")
    q2 = plan_fn30(df.iloc[:cut].reset_index(drop=True), "1h")
    ok30 = all(np.array_equal(
        np.asarray(pd.Series(q1[k]).fillna(False), bool)[:cut],
        np.asarray(pd.Series(q2[k]).fillna(False), bool))
        for k in ("long_event", "short_event"))
    check("R1b truncation causality (QS-030 HTF regime on real data)", ok30)
    ck = E.COSTS["base"]
    p = plan_fn(df, "1h")
    r1 = E.run(df, p, ck["fee"], ck["slip"], 1.0)
    r2 = E.run(df, p, ck["fee"], ck["slip"], 1.0)
    check("R2 determinism", r1["eq"].tolist() == r2["eq"].tolist())


def main():
    OUT.append("QS family-C audit — qs_c_strats.py")
    OUT.append(f"run {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    import hashlib
    for f in ("qs_c_strats.py",):
        with open(os.path.join(HERE, f), "rb") as fh:
            OUT.append(f"{f} sha256: {hashlib.sha256(fh.read()).hexdigest()}")
    OUT.append("")
    c_audit()
    real_audit()
    OUT.append("")
    n_pass = sum(1 for x in OUT if x.startswith("[PASS]"))
    n_fail = sum(1 for x in OUT if x.startswith("[FAIL]"))
    OUT.append(f"TOTAL: {n_pass} PASS, {n_fail} FAIL")
    if FAILED:
        OUT.append("FAILED: " + ", ".join(FAILED))
    text = "\n".join(OUT) + "\n"
    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    with open(RESULTS, "w", encoding="utf-8") as f:
        f.write(text)
    print("\n" + "=" * 70)
    print(text.splitlines()[-1])
    print("written:", RESULTS)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
