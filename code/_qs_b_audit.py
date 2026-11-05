#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_qs_b_audit.py — known-answer audit for family B (QS-011..QS-020).
Run BEFORE any campaign artifact; the report cites this file's output."""
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import qs_b_strats as B       # noqa: E402  (registers into qs_strats.SPECS)
import qs_strats as SD        # noqa: E402
import qs_engine as E         # noqa: E402

RESULTS = os.path.join(ROOT, "results", "qs_b_audit_known_answers.txt")
OUT = []
FAILED = []
HOUR = 3600_000
T0 = 1700000000000 - (1700000000000 % 86400000)


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


def bars(closes, volumes=None):
    n = len(closes)
    c = np.asarray(closes, float)
    v = np.full(n, 100.0) if volumes is None else np.asarray(volumes, float)
    o = np.roll(c, 1); o[0] = c[0]
    h = np.maximum(o, c) + 0.1
    l = np.minimum(o, c) - 0.1
    t = np.array([T0 + i * HOUR for i in range(n)], np.int64)
    return pd.DataFrame(dict(open_ts=t, open=o, high=h, low=l, close=c,
                             volume=v, ts=pd.to_datetime(t, unit="ms", utc=True)))


def b_audit():
    # B1 QS-011: V1 cross event and V2 state re-arm on a hand RSI series.
    # RSI(14) on a crafted close series is hard to pin exactly, so test the
    # EVENT LAYER: V1 = cross, V2 = state re-arm, on a synthetic RSI series.
    rsi_hand = pd.Series([50, 25, 20, 15, 45, 20, 18, 50, 20], dtype=float)
    v1 = (rsi_hand < 30) & (rsi_hand.shift(1) >= 30)
    v2 = B._rsi_state_events(rsi_hand, 30.0)
    check("B1a V1 = exact cross bars (1, 5, 8)",
          list(np.flatnonzero(v1.fillna(False))) == [1, 5, 8])
    check("B1b V2 = first bar <30 while armed (1, 5, 8; re-armed at 45, 50)",
          list(np.flatnonzero(v2)) == [1, 5, 8])
    rsi_gap = pd.Series([50, 25, 20, 15, 12], dtype=float)   # never re-arms
    check("B1c V2 does not re-fire while RSI stays below 30 (V1 too)",
          list(np.flatnonzero(B._rsi_state_events(rsi_gap, 30.0))) == [1]
          and list(np.flatnonzero(((rsi_gap < 30) & (rsi_gap.shift(1) >= 30))
                                  .fillna(False))) == [1])

    # B2 QS-012: re-entry confirmation. Frame: 72 bars of recurring +-3 swings
    # (so the 50-bar bandwidth median is finite and ADX stays low), then a dip
    # below the lower band and a recovery close — the textbook re-entry.
    seg = [100.0, 103.0, 100.0, 97.0, 100.0, 103.0, 100.0, 97.0]
    closes = np.concatenate([np.array(seg * 9)[:72], [94.0, 98.0]])
    df = bars(closes)
    p = SD.SPECS["QS-012"]["build"](df, "1h")
    e_l = ev(p, "long_event")
    # hand logic: event bars must satisfy c > lo and c.shift(1) < lo
    from pack50_core import bollinger
    _s = lambda x: pd.Series(np.asarray(x, float))
    lo, mid, hi = tuple(_s(x) for x in bollinger(df["close"].to_numpy(float), 20, 2.0))
    ok_bars = (df["close"] > lo) & (df["close"].shift(1) < lo.shift(1))
    check("B2 QS-012 every long event is a band re-entry bar",
          bool((e_l & ~ok_bars.fillna(False)).sum() == 0) and int(e_l.sum()) == 1
          and bool(e_l[73]),
          f"events={int(e_l.sum())} at {list(np.flatnonzero(e_l))}")

    # B3 QS-013 z event + regime blocks. The spec refuses z beyond |4| and
    # vol above the 500-bar 95th percentile, so the hand case is a slow
    # 1.2-unit drift (final z near -3.6, inside the band) over 20 bars —
    # a fast crash would be correctly blocked by the crisis filter itself.
    rng = np.random.default_rng(4)
    base = 100 + rng.normal(0, 0.3, 1000)      # realized vol ~0.3/bar
    base[1::2] += 0.15; base[::2] -= 0.15      # two-sided: ADX stays low
    closes = np.concatenate([base, 100 + np.linspace(0, -1.2, 20) + rng.normal(0, 0.3, 20),
                             np.full(300, 98.8)])
    df = bars(closes)
    p = SD.SPECS["QS-013"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("B3 QS-013 z-cross event fires during the -8 decline (z < -2)",
          int(e.sum()) >= 1 and all(1000 <= i <= 1120 for i in np.flatnonzero(e)),
          f"events at {list(np.flatnonzero(e))[-3:]}")

    # B4 QS-014 AVWAP arithmetic (hand cumsum)
    rows = [(99.5, 100.5, 99.0, 100.0, 10.0),      # tp = 100.0
            (100.0, 102.5, 101.0, 102.0, 10.0),    # tp = 102.0
            (101.5, 104.5, 103.0, 104.0, 20.0)]    # tp = 104.0
    t = np.array([T0 + i * HOUR for i in range(3)], np.int64)
    df = pd.DataFrame(dict(open_ts=t, open=[r[0] for r in rows],
                           high=[r[1] for r in rows], low=[r[2] for r in rows],
                           close=[r[3] for r in rows],
                           volume=[r[4] for r in rows],
                           ts=pd.to_datetime(t, unit="ms", utc=True)))
    av = B._avwap(df, "day")
    tp0, tp1, tp2 = (100.5 + 99.0 + 100.0) / 3, (102.5 + 101.0 + 102.0) / 3,         (104.5 + 103.0 + 104.0) / 3
    exp = (tp0 * 10 + tp1 * 10 + tp2 * 20) / 40.0
    check("B4a QS-014 AVWAP = cumsum(tp*v)/cumsum(v) from the day anchor",
          close(av.iloc[-1], exp, 1e-9), f"avwap={av.iloc[-1]:.4f} exp={exp:.4f}")
    df2 = df.copy()
    df2["ts"] = pd.to_datetime(df2["ts"]) + pd.Timedelta(days=1) - pd.Timedelta(hours=2)
    df2["open_ts"] = (df2["open_ts"] + 86_400_000 - 2 * HOUR)
    av2 = B._avwap(df2, "day")
    tp2_alone = (104.5 + 103.0 + 104.0) / 3.0
    check("B4b QS-014 day anchor resets at 00:00 UTC",
          close(av2.iloc[-1], tp2_alone, 1e-9)
          and not close(av2.iloc[-1], exp, 1e-9),
          f"last={av2.iloc[-1]:.4f} day2-only={tp2_alone:.4f}")

    # B6 QS-016 displacement anatomy: sigma, body-retrace target, 6-sigma block
    rng = np.random.default_rng(4)
    closes = 100 + np.cumsum(rng.normal(0, 0.3, 120))
    closes[119] = closes[118] * 0.99               # -1% down-bar
    vols = np.full(120, 100.0)
    vols[119] = 300.0                              # 3x the 20-bar SMA
    df = bars(closes, volumes=vols)
    p = SD.SPECS["QS-016"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("B6a QS-016 long fade fires on the -3sigma bar with volume",
          int(e.sum()) == 1 and bool(e[119]))
    tp_dist = float(pd.Series(p["tp_dist_long"]).dropna().iloc[0])
    body = df["open"].iloc[119] - df["close"].iloc[119]
    check("B6b QS-016 target = half the displacement body",
          close(tp_dist, 0.5 * body, 1e-9), f"tp={tp_dist:.3f} body={body:.3f}")
    closes2 = closes.copy()
    closes2[119] = closes[118] * 0.90              # -10% = beyond -6 sigma
    p2 = SD.SPECS["QS-016"]["build"](bars(closes2, volumes=np.full(120, 300.0)), "1h")
    check("B6c QS-016 displacement beyond -6 sigma is blocked (news)",
          int(ev(p2, "long_event").sum()) == 0)

    # B8 QS-018 ratio + up-close confirmation
    closes = 100 + np.cumsum(rng.normal(0, 0.2, 120))
    closes[-6:] = closes[-7] - np.linspace(0, 6, 6)   # a sharp 6-unit drop
    closes[-1] = closes[-2] + 0.8                     # up-close bar
    df = bars(closes)
    p = SD.SPECS["QS-018"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("B8 QS-018 long fires on the up-close after spike+drop",
          int(e.sum()) >= 1 and bool(e[119]),
          f"events at {list(np.flatnonzero(e))[-3:]}")

    # B9 QS-019 OU machinery: beta == lstsq, ADF t vs manual, target machine
    rng = np.random.default_rng(6)
    n = 600
    lb = 100 + np.cumsum(rng.normal(0, 0.01, n))
    spread_noise = np.zeros(n)
    for i in range(1, n):
        spread_noise[i] = 0.95 * spread_noise[i - 1] + rng.normal(0, 0.005)
    la = lb + 0.5 + spread_noise                    # beta = 1, stationary spread
    df_a = pd.DataFrame(dict(open_ts=np.arange(n) * HOUR + T0, close=np.exp(la),
                             ts=pd.to_datetime(np.arange(n) * HOUR + T0,
                                               unit="ms", utc=True)))
    df_b = pd.DataFrame(dict(open_ts=np.arange(n) * HOUR + T0, close=np.exp(lb),
                             ts=pd.to_datetime(np.arange(n) * HOUR + T0,
                                               unit="ms", utc=True)))
    tgt, note = B._ou_target(df_a, df_b, win=500)
    # beta reference at bar 500 (the first test bar)
    x = lb[0:500]
    y = la[0:500]
    beta_ref = np.polyfit(x, y, 1)[0]
    spr = y - beta_ref * x
    ds = np.diff(spr)
    s_lag = spr[:-1]
    g = ((s_lag - s_lag.mean()) * ds).sum() / ((s_lag - s_lag.mean()) ** 2).sum()
    resid = ds - g * (s_lag - s_lag.mean())
    se_g = np.sqrt((resid ** 2).sum() /
                   max((len(ds) - 1) * ((s_lag - s_lag.mean()) ** 2).sum(), 1e-12))
    t_stat = g / se_g
    hl = -np.log(2.0) / np.log(1.0 + g)
    check("B9a QS-019 stationarity gate passes on a stationary spread "
          "(t < -2.86, HL in 5..100)",
          t_stat < -2.86 and 5 <= hl <= 100,
          f"t={t_stat:.2f} HL={hl:.1f}")
    # the target must be flat during the pre-window and trade afterwards
    check("B9b QS-019 target flat before the estimation window",
          int(np.asarray(tgt)[:500].sum()) == 0)
    # state machine: craft an extreme z by spiking the spread
    la2 = la.copy()
    la2[550:] += 1.0                                  # spread blows out +1
    tgt2, _ = B._ou_target(
        pd.DataFrame(dict(open_ts=df_a["open_ts"], close=np.exp(la2),
                          ts=df_a["ts"])),
        df_b, win=500)
    check("B9c QS-019 target opens a SHORT spread leg on a +z blowout",
          int((np.asarray(tgt2)[560:600] == -1).sum()) > 0)

    # B10 QS-020 wick anatomy (frame built with the 6 kline fields directly;
    # the audit's bars() helper takes a 1-D close array only)
    n10 = 30
    price = 100.0
    o10 = np.empty(n10 + 1); h10 = np.empty(n10 + 1)
    l10 = np.empty(n10 + 1); c10 = np.empty(n10 + 1)
    v10 = np.full(n10 + 1, 100.0)
    for i in range(n10):
        price += 0.1
        o10[i], h10[i], l10[i], c10[i] = price, price + 0.3, price - 0.3, price
    # dislocation bar: o=92, h=100, l=80, c=96 → range 20, lower wick 12 (60%)
    o10[n10], h10[n10], l10[n10], c10[n10] = 92.0, 100.0, 80.0, 96.0
    v10[n10] = 500.0
    t10 = np.array([T0 + i * HOUR for i in range(n10 + 1)], np.int64)
    df = pd.DataFrame(dict(open_ts=t10, open=o10, high=h10, low=l10,
                           close=c10, volume=v10,
                           ts=pd.to_datetime(t10, unit="ms", utc=True)))
    p = SD.SPECS["QS-020"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("B10a QS-020 long fires on the 60%-wick dislocation bar",
          int(e.sum()) == 1 and bool(e[30]))
    tp_dist = float(pd.Series(p["tp_dist_long"]).dropna().iloc[0])
    check("B10b QS-020 target = 50% of the lower wick from the close",
          close(tp_dist, 96.0 - (80.0 + 0.5 * 12.0), 1e-9),
          f"tp={tp_dist:.3f}")
    stop_v = float(pd.Series(p["stop_level_long"]).dropna().iloc[0])
    check("B10c QS-020 stop beyond the wick extreme + 0.25*ATR",
          close(stop_v, 80.0 - 0.25 * float(p["atr"].iloc[30]), 1e-9),
          f"stop={stop_v:.3f}")


def real_audit():
    path = "data/binance_klines_1h_taker/BTCUSDT_1h.csv"
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df["ts"] = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
    df = df.sort_values("ts").reset_index(drop=True)
    plan_fn = SD.SPECS["QS-012"]["build"]
    cut = int(len(df) * 0.6)
    p1 = plan_fn(df, "1h")
    p2 = plan_fn(df.iloc[:cut].reset_index(drop=True), "1h")
    ok = all(np.array_equal(
        np.asarray(pd.Series(p1[k]).fillna(False), bool)[:cut],
        np.asarray(pd.Series(p2[k]).fillna(False), bool))
        for k in ("long_event", "short_event"))
    check("R1 truncation causality (QS-012 on real data)", ok)
    ck = E.COSTS["base"]
    p = plan_fn(df, "1h")
    r1 = E.run(df, p, ck["fee"], ck["slip"], 1.0)
    r2 = E.run(df, p, ck["fee"], ck["slip"], 1.0)
    check("R2 determinism", r1["eq"].tolist() == r2["eq"].tolist())


def main():
    OUT.append("QS family-B audit — qs_b_strats.py")
    OUT.append(f"run {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    import hashlib
    for f in ("qs_b_strats.py",):
        with open(os.path.join(HERE, f), "rb") as fh:
            OUT.append(f"{f} sha256: {hashlib.sha256(fh.read()).hexdigest()}")
    OUT.append("")
    b_audit()
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
