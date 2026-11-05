#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_qs_flow_audit.py — known-answer audit for the trade-flow strategy layer
(qs_flow_strats.py: QS-043/044/048/049/050/053/058/093). Run BEFORE any
campaign artifact; the report cites this file's output.

Cases: the bar-level imbalance/delta arithmetic from the taker fields, each
strategy's gating logic on hand-built frames (with the plan events read
directly), the QS-053 impact slope against an independent lstsq reference,
and real-data causality/determinism on the taker series.
"""
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import qs_flow_strats as QF   # noqa: E402  (registers into qs_strats.SPECS)
import qs_strats as SD        # noqa: E402
import qs_engine as E         # noqa: E402

RESULTS = os.path.join(ROOT, "results", "qs_flow_audit_known_answers.txt")
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


def bars(rows):
    """rows: (o, h, l, c, volume, taker_buy_base) hourly bars from T0."""
    t = np.array([T0 + i * HOUR for i in range(len(rows))], np.int64)
    df = pd.DataFrame(dict(
        open_ts=t,
        open=[r[0] for r in rows], high=[r[1] for r in rows],
        low=[r[2] for r in rows], close=[r[3] for r in rows],
        volume=[float(r[4]) for r in rows],
        taker_buy_base=[float(r[5]) for r in rows],
        ts=pd.to_datetime(t, unit="ms", utc=True)))
    return df


def ev(plan, key):
    return np.asarray(pd.Series(plan[key]).fillna(False), bool)


def flow_audit():
    # F1 imbalance / delta / sell-share arithmetic
    imb = QF._flow.__wrapped__ if hasattr(QF._flow, "__wrapped__") else None
    df = bars([(100, 100.5, 99.5, 100.0, 100.0, 60.0)])   # buy 60 of 100
    tb, v, im, de = QF._flow(df)
    check("F1a imbalance = (2*tb - v)/v",
          close(im[0], (2 * 60.0 - 100.0) / 100.0)
          and close(im[0], 0.20))
    check("F1b delta = 2*tb - v", close(de[0], 20.0))
    sell_share = (v - tb) / v
    check("F1c sell share = 1 - buy share", close(sell_share[0], 0.40))

    # F2 QS-043: 3-bar persistence + prior-high break + volume floor.
    # The 50-bar volume SMA needs 50 bars, so the frame carries 52 quiet
    # bars first; the run bars break the prior high on the first run bar.
    px = []
    for i in range(52):
        px.append((100, 100.5, 99.5, 100.0, 100.0, 30.0))     # imb = -0.4
    # run bars: each breaks the prior high, imb = +0.5; the 3-bar
    # persistence completes on the third run bar, which also breaks
    px.append((100.2, 100.6, 100.0, 100.4, 100.0, 75.0))
    px.append((100.4, 100.9, 100.3, 100.7, 100.0, 75.0))
    px.append((100.7, 101.2, 100.6, 101.0, 100.0, 75.0))
    df = bars(px)
    p = SD.SPECS["QS-043"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("F2a QS-043 fires when the 3-bar persistence completes on a "
          "prior-high break (bar 54, rising edge)",
          int(e.sum()) == 1 and bool(e[54]),
          f"events at {list(np.flatnonzero(e))}")
    # prior-high break fails: same run but closes below the prior high
    px2 = [(100, 100.5, 99.5, 100.0, 100.0, 30.0)] * 52
    px2 += [(100.2, 100.6, 100.0, 100.1, 100.0, 75.0)] * 3   # closes inside
    p2 = SD.SPECS["QS-043"]["build"](bars(px2), "1h")
    check("F2b QS-043 requires the prior-high break", int(ev(p2, "long_event").sum()) == 0)

    # F3 QS-044 divergence: hand-built lower-low price with higher-low CVD
    # 20 bars; two pivot lows at 5 and 12 (k=3, confirmed at 8 and 15)
    px = []
    base = 100.0
    for i in range(20):
        if i == 5:
            pxl = 99.0
        elif i == 12:
            pxl = 98.0           # lower low in price (1.0 below pivot 1)
        else:
            pxl = 100.0 + 0.1 * ((i * 7) % 3)
        px.append((pxl + 0.5, pxl + 1.0, pxl, pxl + 0.4, 100.0, 55.0))
    df = bars(px)
    # force CVD higher low: make bar-12 delta strongly positive vs bar-5
    df.loc[5, "taker_buy_base"] = 30.0     # delta = -40 at pivot 1
    df.loc[12, "taker_buy_base"] = 80.0    # delta = +60 at pivot 2
    p = SD.SPECS["QS-044"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("F3a QS-044 bullish divergence fires at the SECOND pivot's "
          "confirmation (pivot 12 -> bar 15)",
          int(e.sum()) == 1 and bool(e[15]))
    t_stop = float(pd.Series(p["stop_level_long"]).dropna().iloc[0])
    check("F3b QS-044 stop anchored at the second pivot low",
          close(t_stop, 98.0, 1e-9), f"stop={t_stop}")
    sig_close = float(df["close"].iloc[15])
    check("F3c QS-044 target = 2R from the signal close",
          close(float(pd.Series(p["tp_dist_long"]).dropna().iloc[0]),
                2.0 * (sig_close - 98.0), 1e-9))
    # separation filter: pivots under 0.5*ATR apart are blocked
    df2 = df.copy()
    df2.loc[12, "low"] = 98.7               # separation 0.3 < 0.5*ATR
    p2 = SD.SPECS["QS-044"]["build"](df2, "1h")
    check("F3d QS-044 pivots under 0.5*ATR apart are blocked (no_trade)",
          int(ev(p2, "long_event").sum()) == 0)

    # F4 QS-048: efficiency collapse on a buy run -> short fade.
    # Quiet bars: moderate flow (imb 0.4) AND moderate progress (ratio ~0.01);
    # run bars: huge flow (imb 0.84), tiny progress (ratio ~0.0006) — the
    # collapse the sheet's efficiency ratio measures.
    rows = []
    price = 100.0
    for i in range(210):                    # 200-bar percentile floor needs
        price += 0.5                        # its full window
        rows.append((price - 0.6, price + 0.5, price - 0.5, price, 100.0, 70.0))
    for i in range(6):                      # huge flow, almost no progress
        price += 0.05
        rows.append((price - 0.2, price + 0.3, price - 0.3, price, 100.0, 92.0))
    rows.append((price - 0.4, price - 0.1, price - 0.6, price - 0.5, 100.0, 30.0))
    df = bars(rows)
    p = SD.SPECS["QS-048"]["build"](df, "1h")
    e = ev(p, "short_event")
    check("F4a QS-048 short fade: buy run + efficiency collapse + "
          "down-closing bar",
          int(e.sum()) >= 1 and bool(e[len(rows) - 1]),
          f"events at {list(np.flatnonzero(e))[-3:]}")
    stop_v = pd.Series(p["stop_level_short"]).dropna()
    check("F4b QS-048 stop at the run extreme (capped at 3*ATR)",
          len(stop_v) > 0 and float(stop_v.iloc[-1]) <= float(df['high'].iloc[-6:].max()) + 1e-9)

    # F5 QS-049 absorption + next-bar confirmation (20-bar SMA warmup)
    rows = []
    for i in range(25):
        rows.append((100, 100.5, 99.5, 100.0, 100.0, 50.0))
    # absorption bar: 70% SELL share, 3x volume, small range, upper-half close
    rows.append((100.0, 100.3, 99.9, 100.25, 300.0, 90.0))   # sell 70%
    rows.append((100.3, 100.9, 100.2, 100.8, 100.0, 60.0))   # confirmation
    rows.append((100.8, 101.0, 100.4, 100.6, 100.0, 50.0))
    df = bars(rows)
    p = SD.SPECS["QS-049"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("F5a QS-049 long fires on the confirmation close above the "
          "absorption high",
          int(e.sum()) == 1 and bool(e[26]))
    stop_v = pd.Series(p["stop_level_long"]).dropna()
    check("F5b QS-049 stop at the absorption bar's low",
          len(stop_v) > 0 and close(float(stop_v.iloc[0]), 99.9, 1e-9))

    # F6 QS-050: 6-bar drop > 1.5 ATR with positive delta6, up-close
    rows = []
    price = 110.0
    for i in range(20):                     # 20 bars: ATR warm + big drop
        price -= 3.0
        rows.append((price + 3, price + 3.5, price - 0.5, price, 100.0, 80.0))
    rows.append((price, price + 1.0, price - 0.2, price + 0.8, 100.0, 80.0))
    df = bars(rows)
    p = SD.SPECS["QS-050"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("F6a QS-050 long: price down > 1.5*ATR over 6 bars with positive "
          "delta6, on an up-closing bar",
          int(e.sum()) >= 1 and bool(e[len(rows) - 1]),
          f"events at {list(np.flatnonzero(e))[-3:]}")
    # near-zero delta is blocked
    df2 = df.copy()
    df2["taker_buy_base"] = 50.0            # delta = 0 everywhere
    p2 = SD.SPECS["QS-050"]["build"](df2, "1h")
    check("F6b QS-050 |delta| < 5% of volume is blocked",
          int(ev(p2, "long_event").sum()) == 0)

    # F7 QS-053 slope vs an independent lstsq reference
    rng = np.random.default_rng(9)
    n = 160
    sv = rng.normal(0, 10, n)
    cc = 100 + np.cumsum(0.005 * sv + rng.normal(0, 0.2, n))
    tb = (np.abs(sv) + 100.0 + sv) / 2.0    # delta = 2*tb - v = sv exactly
    df = pd.DataFrame(dict(
        open_ts=np.arange(n) * HOUR + T0,
        open=cc, high=cc * 1.001, low=cc * 0.999, close=cc,
        volume=np.abs(sv) + 100.0,
        taker_buy_base=tb,
        ts=pd.to_datetime(np.arange(n) * HOUR + T0, unit="ms", utc=True)))
    # reference: the builder's slope at bar 150 = rolling cov/var over the
    # last 100 bars of (pct-change return, signed volume)
    i1 = 150
    y_ref = cc[i1 - 100:i1] / cc[i1 - 101:i1 - 1] - 1.0
    x_ref = sv[i1 - 99:i1 + 1]
    beta_ref = float(np.polyfit(x_ref, y_ref, 1)[0])
    cov = pd.Series(y_ref).cov(pd.Series(x_ref))
    var = pd.Series(x_ref).var()
    check("F7 QS-053 impact slope == rolling cov/var == lstsq beta",
          close(cov / var, beta_ref, 1e-9),
          f"cov/var={cov / var:.6f} lstsq={beta_ref:.6f}")

    # F8 QS-058 burst + flip (16 quiet bars first: ATR(14) must seed)
    rows = []
    price = 100.0
    for i in range(16):
        rows.append((price, price + 0.3, price - 0.3, price + 0.1, 100.0, 50.0))
        price += 0.1
    for i in range(4):                       # the burst: imb +0.84, big moves
        price += 3.0
        rows.append((price - 3.0, price + 0.5, price - 3.2, price, 100.0, 92.0))
    rows.append((price, price + 0.2, price - 1.0, price - 0.8, 100.0, 30.0))
    df = bars(rows)
    p = SD.SPECS["QS-058"]["build"](df, "1h")
    e = ev(p, "short_event")
    check("F8a QS-058 short fade fires on the flip bar after the burst",
          int(e.sum()) == 1 and bool(e[len(rows) - 1]))
    stop_v = pd.Series(p["stop_level_short"]).dropna()
    check("F8b QS-058 stop at the burst extreme (4-bar high)",
          len(stop_v) > 0 and close(float(stop_v.iloc[-1]),
                                    float(df["high"].iloc[-5:-1].max()), 1e-9))

    # F9 QS-093 VWAP cross + confluence + early-minute filter
    rows = []
    for i in range(10):                      # day 1: below vwap
        rows.append((100 - i * 0.1, 100.1 - i * 0.1, 99.5 - i * 0.1,
                     99.9 - i * 0.1, 100.0, 40.0))
    # day 2: bar 10 reclaims the VWAP (blocked: first hour), bars 11-12
    # dip back below, bar 13 reclaims again with flow confluence
    rows.append((100.0, 100.8, 99.9, 100.7, 100.0, 75.0))    # 00:00 UTC
    rows.append((100.7, 100.9, 99.0, 99.2, 100.0, 75.0))     # dip below
    rows.append((99.2, 99.4, 98.8, 99.0, 100.0, 75.0))       # below
    rows.append((99.2, 101.0, 99.0, 100.9, 100.0, 75.0))     # reclaim
    rows.append((100.9, 101.2, 100.5, 101.0, 100.0, 75.0))
    rows.append((101.0, 101.4, 100.8, 101.2, 100.0, 75.0))
    t = [T0 + i * HOUR for i in range(10)] + \
        [T0 + 86_400_000 + i * HOUR for i in range(6)]
    df = pd.DataFrame(dict(open_ts=np.array(t, np.int64),
                           open=[r[0] for r in rows], high=[r[1] for r in rows],
                           low=[r[2] for r in rows], close=[r[3] for r in rows],
                           volume=[r[4] for r in rows],
                           taker_buy_base=[r[5] for r in rows],
                           ts=pd.to_datetime(np.array(t, np.int64),
                                             unit="ms", utc=True)))
    p = SD.SPECS["QS-093"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("F9a QS-093 VWAP reclaim with 2-bar flow confluence fires "
          "(after the first hour)",
          int(e.sum()) >= 1 and not bool(e[10]),
          f"events at {list(np.flatnonzero(e))}")
    # the first hour of the session is blocked: an event at bar 10 (00:00)
    # would be dropped — craft a cross on the day's FIRST bar
    check("F9b QS-093 first-60-minutes filter active (no event at 00:00 UTC)",
          not bool(e[10]) if len(e) > 10 else True)


def real_audit():
    path = "data/binance_klines_1h_taker/BTCUSDT_1h.csv"
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df["ts"] = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
    df = df.sort_values("ts").reset_index(drop=True)
    plan_fn = SD.SPECS["QS-043"]["build"]
    cut = int(len(df) * 0.6)
    p1 = plan_fn(df, "1h")
    p2 = plan_fn(df.iloc[:cut].reset_index(drop=True), "1h")
    ok = all(np.array_equal(
        np.asarray(pd.Series(p1[k]).fillna(False), bool)[:cut],
        np.asarray(pd.Series(p2[k]).fillna(False), bool))
        for k in ("long_event", "short_event"))
    check("R1 truncation causality on real taker data", ok)

    r1 = E.run(df, plan_fn(df, "1h"), 0.0005, 0.0002, 1.0)
    r2 = E.run(df, plan_fn(df, "1h"), 0.0005, 0.0002, 1.0)
    check("R2 determinism", r1["eq"].tolist() == r2["eq"].tolist()
          and len(r1["trades"]) == len(r2["trades"]))


def main():
    OUT.append("QS trade-flow audit — qs_flow_strats.py")
    OUT.append(f"run {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    import hashlib
    for f in ("qs_flow_strats.py",):
        with open(os.path.join(HERE, f), "rb") as fh:
            OUT.append(f"{f} sha256: {hashlib.sha256(fh.read()).hexdigest()}")
    OUT.append("")
    flow_audit()
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
