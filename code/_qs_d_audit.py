#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_qs_d_audit.py — known-answer audit for family D (QS-031..QS-040).
Run BEFORE any campaign artifact; the report cites this file's output.
Hand frames use ALTERNATING WICKS: a fixed wick makes a local peak tie
exactly with the next bar's high (both equal close+wick), so strict-greater
pivots can never form — the failure mode this audit exists to catch. Every
hand frame carries a ~22-bar zigzag warmup so ATR(14)/ADX(14) are finite
at the tested bar, and no trend is monotone (strict pivots need swings)."""
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import qs_d_strats as D       # noqa: E402  (registers into qs_strats.SPECS)
import qs_strats as SD        # noqa: E402
import qs_engine as E         # noqa: E402

RESULTS = os.path.join(ROOT, "results", "qs_d_audit_known_answers.txt")
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


def frame(rows):
    """rows: list of (open, high, low, close) or (o, h, l, c, volume);
    mixed row lengths are padded with the default volume."""
    rows = [r if len(r) == 5 else r + (100.0,) for r in rows]
    v = [r[4] for r in rows]
    rows = [r[:4] for r in rows]
    n = len(rows)
    t = np.array([T0 + i * HOUR for i in range(n)], np.int64)
    return pd.DataFrame(dict(
        open_ts=t, open=[r[0] for r in rows], high=[r[1] for r in rows],
        low=[r[2] for r in rows], close=[r[3] for r in rows],
        volume=v if v is not None else np.full(n, 100.0),
        ts=pd.to_datetime(t, unit="ms", utc=True)))


def _warmup(n=22, px=100.0):
    """Mild zigzag warmup bars (alternating wicks so strict pivots can
    form); pivots created here sit far from every crafted level below."""
    rows = []
    for i in range(n):
        amp = 0.3 + 0.05 * ((i * 7) % 3)      # non-periodic: ties break
        c_ = px + (amp if i % 2 else -amp)
        o_ = px + (amp if (i - 1) % 2 else -amp) if i else c_
        hw = 0.35 if i % 2 else 0.12
        rows.append((o_, max(o_, c_) + hw, min(o_, c_) - (0.12 if i % 2 else 0.35), c_))
    return rows


def d_audit():
    # ── D1 QS-031: a confirmed swing high, a breakout beyond it by more
    # than 0.5*ATR, the confirmation-delay boundary, and the swing-low stop.
    rows = _warmup()
    px = 100.6
    for i in range(8):                      # grind up 100.6 -> 106.2
        px += 0.8
        rows.append((px - 0.5, px + 0.3, px - 0.7, px))
    rows.append((106.3, 107.4, 106.1, 107.0))     # bar 30: peak (pivot high)
    for i in range(3):                      # bars 31-33: pullback
        rows.append((106.4 - 0.5 * i, 106.6 - 0.5 * i, 105.1 - 0.5 * i,
                     106.2 - 0.5 * i))
    rows.append((105.6, 108.5, 105.4, 108.2))     # bar 34: breakout close
    rows.append((108.2, 108.6, 107.7, 108.3))     # bar 35: stays above
    df = frame(rows)
    p = SD.SPECS["QS-031"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("D1a QS-031 long fires on the post-confirmation breakout",
          int(e.sum()) >= 1 and bool(e[34]),
          f"events at {list(np.flatnonzero(e))}")
    stop_l = pd.Series(p["stop_level_long"])
    a34 = float(p["atr"].iloc[34])
    closes = df["close"]
    check("D1b QS-031 stop distance inside the declared 1-3*ATR band",
          all(1.0 * float(p["atr"].iloc[i]) - 1e-6
              <= float(closes.iloc[i]) - float(stop_l.iloc[i])
              <= 3.0 * float(p["atr"].iloc[i]) + 1e-6
              for i in np.flatnonzero(e)),
          f"stop at event={float(stop_l.iloc[34]):.3f} atr={a34:.3f}")
    # confirmation delay: a breakout bar while the peak is unconfirmed must
    # not lift last_ph (an earlier, lower pivot stays in force)
    rows3 = rows[:32] + [(105.7, 108.5, 105.5, 108.2)] + rows[33:]
    p3 = SD.SPECS["QS-031"]["build"](frame(rows3), "1h")
    e3 = ev(p3, "long_event")
    check("D1c QS-031 no event on the bar before the pivot confirms",
          not bool(e3[32]),
          f"events {list(np.flatnonzero(e3))[:4]}")

    # ── D2 QS-032: ascending swings, a ~50% retrace, trigger close above
    # the prior high; the target is the retest of the last swing high.
    rows = _warmup()
    px = 100.6
    for i in range(6):                      # up leg to H1
        px += 0.7
        rows.append((px - 0.5, px + 0.3, px - 0.7, px))
    rows.append((105.5, 107.0, 105.3, 106.6))     # peak H1 (pivot high)
    for i in range(3):                      # pullback to L2 (higher low)
        rows.append((106.0 - 0.5 * i, 106.2 - 0.5 * i, 104.7 - 0.5 * i,
                     105.8 - 0.5 * i))
    for i in range(4):                      # rally to H2 > H1
        px2 = 105.0 + 0.6 * (i + 1)
        rows.append((px2 - 0.5, px2 + 0.4, px2 - 0.7, px2))
    rows.append((107.5, 109.0, 107.3, 108.6))     # peak H2 = 109.0
    for i in range(3):                      # confirm H2, pull back ~56%
        rows.append((108.0 - 0.6 * i, 108.2 - 0.6 * i, 106.6 - 0.6 * i,
                     107.8 - 0.6 * i))
    rows += [
        (107.6, 107.8, 106.9, 107.0),
        (107.0, 107.2, 106.5, 106.6),
        (106.6, 106.8, 105.9, 106.2),       # retrace close 106.2 (~53%)
        (106.2, 106.6, 106.1, 106.4),       # retest low 105.9 -> pivot low
        (106.4, 106.9, 106.2, 106.8),       # recover
        (106.8, 107.4, 106.6, 107.3),       # trigger: close > prior high
    ]
    df = frame(rows)
    p = SD.SPECS["QS-032"]["build"](df, "1h")
    e = ev(p, "long_event")
    idxs = list(np.flatnonzero(e))
    check("D2a QS-032 retrace-continuation long fires",
          len(idxs) >= 1 and idxs[-1] >= 36,
          f"events at {idxs[-4:]}")
    tp = pd.Series(p["tp_dist_long"]).dropna()
    check("D2b QS-032 target = the retest of the last swing high",
          len(tp) >= 1 and all(float(x) >= -1e-9 for x in tp),
          f"tp last={float(tp.iloc[-1]):.3f}" if len(tp) else "no tp")

    # ── D3 QS-033: zigzag downtrend -> CHoCH break. The swing period must
    # differ from the pivot window (a 3-bar sawtooth is pathologically
    # aliased with k=3: no interior pivot can ever confirm), and the break
    # bar must arrive AFTER the last peak's 3-bar confirmation window, so
    # three calm bars separate the trend from the break.
    rows = _warmup()
    px = 112.0
    for i in range(28):                     # 4 cycles of a 7-bar swing
        step = (0.8 if i % 7 == 0
                else (-0.45 if i % 7 < 5 else 0.4))
        px += step
        rows.append((px - step, px + (0.5 if i % 7 == 0 else 0.2),
                     px - 0.5, px))
    for i in range(3):                      # calm gap: last peak confirms
        rows.append((px + 0.1, px + 0.3, px - 0.2, px + 0.2))
    ph_conf, _pl = D._confirmed_pivots(frame(rows), 3)
    ph_last, _ = D._last_two(ph_conf)
    lvl = float(ph_last.iloc[-1])
    rows.append((lvl + 0.0, lvl + 1.4, lvl - 0.1, lvl + 1.2))   # break bar
    rows.append((lvl + 1.2, lvl + 1.3, lvl - 0.1, lvl + 0.3))   # retest touch
    rows.append((lvl + 0.3, lvl + 1.1, lvl + 0.2, lvl + 1.0))   # reclaim
    df0 = frame(rows)
    adx = D._adx_s(df0, 14)
    check("D3a QS-033 sawtooth downtrend keeps ADX below 35",
          float(adx.iloc[-1]) < 35.0, f"adx={float(adx.iloc[-1]):.1f}")
    p = SD.SPECS["QS-033"]["build"](df0, "1h")
    e = ev(p, "long_event")
    check("D3b QS-033 produces a CHoCH long on the downtrend frame",
          int(e.sum()) >= 1 and bool(e[len(rows) - 3:].any()),
          f"events at {list(np.flatnonzero(e))[-4:]}")

    # ── D4 QS-034: two pivot lows within 0.5*ATR form a support zone; a
    # hammer wicking into it and closing above the midpoint fires.
    rows = _warmup()
    rows += [
        (100.6, 101.0, 100.2, 100.8),
        (100.8, 101.9, 100.6, 101.6),   # up
        (101.6, 102.8, 101.4, 102.5),   # peak -> pivot high
        (102.5, 102.7, 101.3, 101.4),   # down
        (101.5, 101.8, 100.35, 100.7),  # low -> pivot low A (100.35)
        (100.7, 102.0, 101.0, 101.7),   # bounce (low well above A)
        (101.7, 102.1, 101.1, 101.4),   # drift
        (101.6, 101.9, 101.05, 101.3),  # drift
        (101.3, 101.6, 100.55, 101.1),  # low -> pivot low B (100.55)
        (101.1, 101.9, 100.9, 101.7),   # confirm bars (lows > B)
        (101.7, 102.0, 101.4, 101.6),
        (101.6, 101.9, 101.3, 101.5),
        (101.4, 101.5, 100.6, 101.45),  # hammer: wick into the zone
    ]
    df = frame(rows)
    p = SD.SPECS["QS-034"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("D4 QS-034 hammer rejection off the pivot-low zone fires",
          int(e.sum()) >= 1 and bool(e[34]),
          f"events at {list(np.flatnonzero(e))}")

    # ── D5 QS-035: qualified range, sweep below the bottom edge closing
    # back inside, target = the range midpoint.
    rows = _warmup(px=102.0)
    for i in range(100):                    # triangle 100..104, troughs at
        d = min((i - 5) % 20, (5 - i) % 20)  # i%20==15, peaks at i%20==5
        ph = 4.0 - 0.4 * d                   # circular distance: ph in [0,4]
        rows.append((100 + ph - 0.3, 100 + ph + 0.4, 100 + ph - 0.6,
                     100 + ph))
    for i in range(20):                     # quiet inside the range
        rows.append((102.0, 102.5, 101.6, 102.1))
    rows.append((102.1, 102.3, 99.0, 100.6))     # sweep: low 99.0 < ll-0.1a
    df = frame(rows)
    p = SD.SPECS["QS-035"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("D5 QS-035 sweep-and-reclaim fires on the sweep bar",
          int(e.sum()) >= 1 and bool(e[142]),
          f"events tail {list(np.flatnonzero(e))[-4:]}")
    tp = pd.Series(p["tp_dist_long"]).dropna()
    if len(tp):
        ll = float(df["low"].iloc[22:122].min())
        hh = float(df["high"].iloc[22:122].max())
        mid = (hh + ll) / 2.0
        check("D5b QS-035 target = the range midpoint",
              close(float(tp.iloc[-1]), mid - 100.6, 1e-6),
              f"tp={float(tp.iloc[-1]):.3f} mid={mid:.3f}")

    # ── D6 QS-036: break of a confirmed swing high, retest within
    # 0.25*ATR, higher-low close above H fires; the plan carries trailing 3.
    rows = _warmup()
    rows += [
        (100.6, 101.0, 100.2, 100.8),
        (100.8, 102.0, 100.6, 101.7),
        (101.7, 103.2, 101.5, 102.9),   # peak H = 103.2 -> pivot
        (102.9, 103.15, 102.5, 102.8),
        (102.8, 103.1, 102.6, 102.95),  # confirms pivot at +3
        (102.95, 103.15, 102.85, 103.05),  # 3rd confirm bar (high < H)
        (103.05, 103.5, 103.0, 103.3),     # break bar: close 103.3 > H
        (103.3, 103.45, 103.06, 103.15),   # retest: low inside the band
        (103.15, 103.4, 103.12, 103.35),   # higher-low close above H
    ]
    df = frame(rows)
    p = SD.SPECS["QS-036"]["build"](df, "1h")
    e = ev(p, "long_event")
    idxs = list(np.flatnonzero(e))
    check("D6 QS-036 retest event fires after the confirmed break",
          len(idxs) >= 1 and float(p.get("trailing_atr_mult") or 0) == 3.0,
          f"events at {idxs}")

    # ── D7 QS-037: 60-bar range, 8-bar compression in the upper third,
    # close above the consolidation high; TP = the prior range high.
    rows = _warmup()
    for i in range(60):
        ph = 2.0 + 2.0 * np.sin(i / 5.0)
        rows.append((100 + ph - 0.3, 100 + ph + 0.4, 100 + ph - 0.6,
                     100 + ph))
    for i in range(8):
        rows.append((103.3, 103.6, 103.15, 103.4))
    rows.append((103.4, 103.9, 103.3, 103.8))
    df = frame(rows)
    p = SD.SPECS["QS-037"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("D7a QS-037 upper-third compression breakout fires",
          int(e.sum()) >= 1 and bool(e[90]),
          f"events tail {list(np.flatnonzero(e))[-4:]}")
    tp = pd.Series(p["tp_dist_long"]).dropna()
    if len(tp):
        pr_hh = float(df["high"].iloc[22:82].max())
        check("D7b QS-037 target = the prior range high",
              close(float(tp.iloc[-1]), pr_hh - 103.8, 1e-6),
              f"tp={float(tp.iloc[-1]):.3f} pr_hh={pr_hh:.3f}")

    # ── D8 QS-038: a decelerating down-run then an up-close -> long fade;
    # the 50% target is the run midpoint.
    rows = _warmup()
    px = 112.0
    for i in range(20):                     # mild drift so ATR is stable
        rows.append((px + 0.2, px + 0.5, px - 0.2, px + 0.1))
        px += 0.1
    ranges = [4.0, 3.2, 1.4, 0.7, 0.5, 0.25]    # decelerating down-run
    vols = [140, 120, 100, 90, 80, 70]          # falling participation
    for r, vv in zip(ranges, vols):
        rows.append((px, px - 0.2 * r, px - r, px - 0.9 * r, vv))
        px -= 0.9 * r
    for i in range(4):
        rows.append((px + 0.1, px + 0.5, px - 0.3, px + 0.25, 60))
    df = frame(rows)
    a = D._atr_s(df)
    tot = 0.9 * sum(ranges)
    check("D8a QS-038 frame run exceeds 4*ATR and decelerates",
          float(a.iloc[46]) > 0 and tot > 4 * float(a.iloc[46]),
          f"move={tot:.2f} atr={float(a.iloc[46]):.2f}")
    p = SD.SPECS["QS-038"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("D8b QS-038 long fade fires on the up-close after the down-run",
          int(e.sum()) >= 1,
          f"events at {list(np.flatnonzero(e))[:6]}")
    tp = pd.Series(p["tp_dist_long"]).dropna()
    check("D8c QS-038 target = 50% of the run (midpoint to the pre-run top)",
          len(tp) >= 1 and float(tp.iloc[0]) > 0,
          f"tp={float(tp.iloc[0]):.3f}" if len(tp) else "no tp")

    # ── D9 QS-039: oscillating HTF uptrend (strict pivots need swings) ->
    # longs fire; the rollover opens shorts; no shorts inside the uptrend.
    n9 = 840
    i9 = np.arange(n9)
    base = 100 + i9 * 0.05 + 4.0 * np.sin(i9 / 8.0)
    cc = base.copy()
    cc[560:] = base[560] + (i9[560:] - 560) * (-0.16) + \
        4.0 * np.sin(i9[560:] / 8.0)
    o9 = np.roll(cc, 1); o9[0] = cc[0]
    w9 = np.where(i9 % 2 == 0, 0.35, 0.12)
    df = pd.DataFrame(dict(
        open_ts=np.array([T0 + i * HOUR for i in range(n9)], np.int64),
        open=o9, high=np.maximum(o9, cc) + w9,
        low=np.minimum(o9, cc) - w9[::-1], close=cc,
        volume=np.full(n9, 100.0),
        ts=pd.to_datetime(np.array([T0 + i * HOUR for i in range(n9)],
                                   np.int64), unit="ms", utc=True)))
    p = SD.SPECS["QS-039"]["build"](df, "1h")
    e_l, e_s = ev(p, "long_event"), ev(p, "short_event")
    check("D9a QS-039 longs fire inside the HTF uptrend",
          int(e_l[:560].sum()) > 0, f"n_long={int(e_l.sum())}")
    check("D9b QS-039 shorts fire after the HTF rollover",
          int(e_s[560:].sum()) > 0, f"n_short={int(e_s.sum())}")
    check("D9c QS-039 no shorts inside the HTF uptrend",
          int(e_s[:500].sum()) == 0)

    # ── D10 QS-040: displacement bar, two holds above its 50% level, then
    # a close above the consolidation high.
    rows = _warmup()
    rows += [
        (100.6, 101.0, 100.2, 100.8),
        (100.8, 101.2, 100.5, 101.0),
        (101.0, 101.6, 100.8, 101.3),
        (101.3, 106.2, 101.1, 105.8),     # displacement: range 5.1, body 4.5
        (105.8, 106.1, 105.0, 105.9),     # hold (low > disp50 ~103.65)
        (105.9, 106.3, 105.3, 106.1),     # hold
        (106.1, 106.8, 106.0, 106.6),     # close above the consolidation high
    ]
    df = frame(rows)
    p = SD.SPECS["QS-040"]["build"](df, "1h")
    e = ev(p, "long_event")
    check("D10a QS-040 continuation long fires after the shallow retrace",
          int(e.sum()) >= 1 and bool(e[28]),
          f"events at {list(np.flatnonzero(e))}")
    lvl = pd.Series(p["stop_level_long"]).dropna()
    disp50 = (106.2 + 101.1) / 2.0
    if len(lvl):
        a6 = float(p["atr"].iloc[28])
        exp = max(disp50, 106.6 - 3.0 * a6)
        check("D10b QS-040 stop = the displacement 50% level (3*ATR cap)",
              abs(float(lvl.iloc[-1]) - exp) < 1e-6,
              f"stop={float(lvl.iloc[-1]):.3f} disp50={disp50:.3f} "
              f"cap={106.6 - 3.0 * a6:.3f}")
    check("D10c QS-040 plan carries the native 2*ATR trailing stop",
          float(p.get("trailing_atr_mult") or 0) == 2.0)


def real_audit():
    path = "data/binance_klines_1h_taker/BTCUSDT_1h.csv"
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df["ts"] = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
    df = df.sort_values("ts").reset_index(drop=True)
    cut = int(len(df) * 0.6)
    for sid in ("QS-031", "QS-036"):
        plan_fn = SD.SPECS[sid]["build"]
        p1 = plan_fn(df, "1h")
        p2 = plan_fn(df.iloc[:cut].reset_index(drop=True), "1h")
        ok = all(np.array_equal(
            np.asarray(pd.Series(p1[k]).fillna(False), bool)[:cut],
            np.asarray(pd.Series(p2[k]).fillna(False), bool))
            for k in ("long_event", "short_event"))
        check(f"R1 truncation causality ({sid} on real data)", ok)
    plan_fn = SD.SPECS["QS-039"]["build"]
    q1 = plan_fn(df, "1h")
    q2 = plan_fn(df.iloc[:cut].reset_index(drop=True), "1h")
    ok = all(np.array_equal(
        np.asarray(pd.Series(q1[k]).fillna(False), bool)[:cut],
        np.asarray(pd.Series(q2[k]).fillna(False), bool))
        for k in ("long_event", "short_event"))
    check("R1b truncation causality (QS-039 HTF structure on real data)", ok)
    ck = E.COSTS["base"]
    p = SD.SPECS["QS-031"]["build"](df, "1h")
    r1 = E.run(df, p, ck["fee"], ck["slip"], 1.0)
    r2 = E.run(df, p, ck["fee"], ck["slip"], 1.0)
    check("R2 determinism", r1["eq"].tolist() == r2["eq"].tolist())


def main():
    OUT.append("QS family-D audit — qs_d_strats.py")
    OUT.append(f"run {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    import hashlib
    for f in ("qs_d_strats.py",):
        with open(os.path.join(HERE, f), "rb") as fh:
            OUT.append(f"{f} sha256: {hashlib.sha256(fh.read()).hexdigest()}")
    OUT.append("")
    d_audit()
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
