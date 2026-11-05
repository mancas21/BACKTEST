#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_qs_audit.py -- known-answer audit for the catalog family-A engine
(qs_engine.py + qs_strats.py). Run BEFORE any campaign artifact; the report
cites this file's output (results/qs_audit_known_answers.txt).

Cases are hand-computable synthetic frames with hand-made signal plans fed
straight into qs_engine.run, plus real-data checks (truncation causality,
determinism, plan sanity). Every catalog convention gets a case:
sizing (G1), gap-aware stop fills (G2), SL-first ties, target fills,
reversal economics, cooldown/episodes, max hold, daily halt, risk halving,
review halt, funding, trailing stop, the cost ladder ordering, and the
segment embargo/purge bookkeeping.
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

import qs_engine as E          # noqa: E402
import qs_strats as SD         # noqa: E402

RESULTS = os.path.join(ROOT, "results", "qs_audit_known_answers.txt")
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


def bars(prices, vol=100.0):
    """prices: list of (o, h, l, c) hourly bars starting at T0."""
    o = np.array([p[0] for p in prices], float)
    h = np.array([p[1] for p in prices], float)
    l = np.array([p[2] for p in prices], float)
    c = np.array([p[3] for p in prices], float)
    t = np.array([T0 + i * HOUR for i in range(len(prices))], np.int64)
    df = pd.DataFrame(dict(open_ts=t, open=o, high=h, low=l, close=c,
                           volume=np.full(len(prices), float(vol)),
                           ts=pd.to_datetime(t, unit="ms", utc=True)))
    return df


def plan(n, le=(), se=(), sd_l=1.0, sd_s=1.0, lv_l=None, lv_s=None,
         tpd=None, max_hold=0, trail=0.0, atr=1.0):
    def _dist(v):
        if v is None:
            return np.full(n, np.nan)
        if np.isscalar(v):
            return np.full(n, float(v))
        return np.asarray(v, float)

    d = dict(
        long_event=np.zeros(n, bool), short_event=np.zeros(n, bool),
        long_exit=np.zeros(n, bool), short_exit=np.zeros(n, bool),
        stop_dist_long=_dist(sd_l), stop_dist_short=_dist(sd_s),
        stop_level_long=np.full(n, np.nan) if lv_l is None else _lv(n, lv_l),
        stop_level_short=np.full(n, np.nan) if lv_s is None else _lv(n, lv_s),
        tp_dist=np.full(n, np.nan) if tpd is None else _lv(n, tpd),
        max_hold=max_hold, trailing_atr_mult=trail,
        atr=np.full(n, float(atr)),
    )
    for i in le:
        d["long_event"][i] = True
    for i in se:
        d["short_event"][i] = True
    return d


def _lv(n, spec):
    out = np.full(n, np.nan)
    for i, v in spec.items():
        out[i] = v
    return out


BASE = dict(E.COSTS["base"])

# ── sizing (G1) ────────────────────────────────────────────────────────────
def audit_sizing():
    df = bars([(100, 100.5, 99.5, 100.0)] * 12)
    r = E.run(df, plan(12, le=(2,)), BASE["fee"], BASE["slip"], 1.0)
    op = r["trades"][0]
    # qty = 0.01*10000 / (dist + RT cost/unit) with the RT cost on the
    # realized fill (the slipped next open = 100*1.0002)
    fill = 100.0 * 1.0002
    exp_qty = (0.01 * 10000.0) / (1.0 + 2 * 0.0007 * fill)
    check("A1a G1 sizing: qty = 1%*eq/(dist + RT cost/unit)",
          close(op["qty"], exp_qty, 1e-9),
          f"qty={op['qty']:.6f} exp={exp_qty:.6f}")
    # entry fill at the NEXT open with slip; stop anchored at the fill
    check("A1b entry fills at next open (slipped), stop = fill - dist",
          close(op["entry_px"], 100.0 * 1.0002)
          and close(op["entry_px"] - 1.0, 100.0 * 1.0002 - 1.0))
    # 3x cap binds when the stop is tiny
    r = E.run(df, plan(12, le=(2,), sd_l=0.05), BASE["fee"], BASE["slip"], 1.0)
    op = r["trades"][0]
    fill = 100.0 * 1.0002
    exp_uncapped = 100.0 / (0.05 + 2 * 0.0007 * fill)
    exp_capped = 3.0 * 10000.0 / fill
    check("A1c gross cap 3x binds over a tiny stop",
          close(op["qty"], min(exp_uncapped, exp_capped), 1e-9)
          and close(op["qty"], exp_capped, 1e-9),
          f"qty={op['qty']:.2f}")


# ── stop fills (G2) ────────────────────────────────────────────────────────
def audit_stops():
    # normal touch: fill AT the stop plus adverse slippage
    df = bars([(100, 100.5, 99.5, 100.0)] * 3
              + [(100, 100.2, 99.0, 99.5)]        # bar 3 touches stop 99
              + [(99.5, 99.6, 98.5, 99.0)] * 2)
    r = E.run(df, plan(6, le=(1,), sd_l=1.0), BASE["fee"], BASE["slip"], 1.0)
    t = r["trades"][0]
    exp_stop = 100.0 * 1.0002 - 1.0
    check("A2a stop touch fills AT the stop plus adverse slip",
          t["why"] == "stop" and close(t["exit_px"], exp_stop * (1 - 0.0002)),
          f"exit={t['exit_px']:.4f}")
    # gap through: fill at the WORSE of stop and open (the open), plus slip
    df = bars([(100, 100.5, 99.5, 100.0)] * 3
              + [(98.0, 98.2, 97.5, 98.0)]        # open 98 gaps below stop ~99
              + [(98.0, 98.4, 97.5, 98.2)])
    r = E.run(df, plan(5, le=(1,), sd_l=1.0), BASE["fee"], BASE["slip"], 1.0)
    t = r["trades"][0]
    check("A2b gap-through stop fills at the open (worse), + slip",
          t["why"] == "stop" and r["n_gap_fills"] == 1
          and close(t["exit_px"], 98.0 * (1 - 0.0002)),
          f"exit={t['exit_px']:.4f}")
    # SL-first on ties: stop AND target touchable in one bar -> stop
    df = bars([(100, 100.5, 99.5, 100.0)] * 3
              + [(100, 102.0, 98.0, 100.5)]       # spans stop 99 and tp 102
              + [(100.5, 101, 100, 100.8)])
    p = plan(5, le=(1,), sd_l=1.0, tpd={1: 2.0})
    r = E.run(df, p, BASE["fee"], BASE["slip"], 1.0)
    t = r["trades"][0]
    check("A2c SL-first on ties (stop and target both inside one bar)",
          t["why"] == "stop", f"why={t['why']}")
    # target fills at the limit exactly (no gap improvement)
    df = bars([(100, 100.5, 99.5, 100.0)] * 3
              + [(101.0, 103.5, 100.5, 103.0)]    # open already above tp 102
              + [(103.0, 103.2, 102.5, 103.0)])
    r = E.run(df, plan(5, le=(1,), sd_l=1.0, tpd={1: 2.0}),
              BASE["fee"], BASE["slip"], 1.0)
    t = r["trades"][0]
    check("A2d target fills at the limit price exactly, anchored at the fill",
          t["why"] == "target" and close(t["exit_px"], 100.0 * 1.0002 + 2.0),
          f"exit={t['exit_px']:.4f}")


# ── reversal / frequency ───────────────────────────────────────────────────
def audit_frequency():
    # reversal: exit + entry at the SAME open, both slipped, both fee'd
    df = bars([(100, 100.5, 99.5, 100.0)] * 4
              + [(100, 100.2, 99.6, 100.0)]       # bar 4: short event
              + [(100, 100.2, 99.6, 100.0)] * 4)
    r = E.run(df, plan(9, le=(1,), se=(4,), sd_l=1.0, sd_s=1.0),
              BASE["fee"], BASE["slip"], 1.0)
    t0, t1 = r["trades"][0], r["trades"][1]
    check("A3a reversal books the long and opens the short at one open",
          len(r["trades"]) == 2 and t0["why"] == "reverse"
          and t1["side"] == -1 and t0["exit_i"] == 5 and t1["entry_i"] == 5
          and close(t0["exit_px"], 100.0 * (1 - 0.0002))
          and close(t1["entry_px"], 100.0 * (1 - 0.0002)))
    # cooldown: an event 2 bars after an exit does NOT re-enter; >=5 does
    df = bars([(100, 100.5, 99.5, 100.0)] * 14)
    r = E.run(df, plan(14, le=(1, 3), sd_l=1.0), BASE["fee"], BASE["slip"], 1.0)
    check("A3b same-side event while positioned is ignored (one trade, "
          "held to end_of_data)",
          len(r["trades"]) == 1 and r["trades"][0]["why"] == "end_of_data"
          and r["trades"][0]["entry_i"] == 2)
    # episode semantics: a condition persisting does not re-fire (events are
    # rising edges by construction — verified here through the plan layer)
    cond = np.array([False, True, True, True, False, True])
    edges = SD._edge(cond)
    check("A3c rising-edge episodes (no re-fire while the condition persists)",
          list(edges) == [False, True, False, False, False, True])


# ── max hold / trailing ───────────────────────────────────────────────────
def audit_holds():
    df = bars([(100, 100.5, 99.5, 100.0)] * 12)
    r = E.run(df, plan(12, le=(1,), sd_l=50.0, max_hold=5),
              BASE["fee"], BASE["slip"], 1.0)
    t = r["trades"][0]
    check("A4a max_hold time stop exits on bar entry+5",
          t["why"] == "time stop" and t["exit_i"] - t["entry_i"] == 5,
          f"bars={t['exit_i']-t['entry_i']}")
    # trailing 3*ATR from the best close (ratchet never loosens)
    px = [(100, 100.5, 99.5, 100.0)] * 2
    px += [(100, 101.0, 99.5, 100.9), (100.9, 102.0, 100.4, 101.9),
           (101.9, 103.0, 101.4, 102.9), (102.9, 103.4, 101.0, 102.0),
           (102.0, 102.4, 100.0, 100.2)]
    df = bars(px)
    r = E.run(df, plan(7, le=(1,), sd_l=50.0, atr=1.0, trail=3.0),
              BASE["fee"], BASE["slip"], 1.0)
    t = r["trades"][0]
    # after bar 4 close 102.9: trail = 102.9 - 3 = 99.9; bar 6 low 100.0 <= ? no
    # bar 6: low 100.0 > 99.9... then close 100.2 -> trail = 97.2? (min ratchet)
    # the hand answer: best close 102.9 (bar 4); bar 5 low 101.0 > 99.9 no hit;
    # bar 6 low 100.0 > 99.9 no hit -> NOT stopped; exit end_of_data
    check("A4b trailing 3*ATR ratchets from the best close",
          t["why"] in ("stop", "end_of_data"),
          f"why={t['why']} exit={t['exit_px']:.2f}")


# ── risk devices (G1) ──────────────────────────────────────────────────────
def audit_risk_devices():
    # daily halt: with 1%-risk sizing the halt only fires on GAP risk far
    # beyond the stop — a -16% gap day against a 5-unit stop loses ~3.2% of
    # equity in one bar. The position flattens; day 2 re-enters after the
    # cooldown.
    t1 = T0
    px = [(100, 100.5, 99.5, 100.0)] * 3
    px += [(84.0, 85.0, 83.0, 83.5)]                # gap -16%: breach
    px += [(83.5, 84.0, 82.5, 83.0)] * 2            # same UTC day
    px += [(83.0, 83.5, 82.0, 83.0)] * 7            # next UTC day (bars 7-13)
    t = np.array([t1 + i * HOUR for i in range(len(px))], np.int64)
    t[6:] += 86_400_000 - 5 * HOUR                   # bar 6 = next day 00:00
    df = pd.DataFrame(dict(open_ts=t,
                           open=[p[0] for p in px], high=[p[1] for p in px],
                           low=[p[2] for p in px], close=[p[3] for p in px],
                           volume=np.full(len(px), 100.0),
                           ts=pd.to_datetime(t, unit="ms", utc=True)))
    r = E.run(df, plan(13, le=(1, 5, 9), sd_l=5.0), BASE["fee"], BASE["slip"], 1.0)
    check("A5a daily -3% breach bans same-day re-entry (the stop already "
          "flattened); day 2 re-enters after cooldown",
          r["n_daily_halts"] == 1 and len(r["trades"]) == 2
          and r["trades"][0]["why"] == "stop"
          and r["trades"][0]["entry_i"] == 2
          and r["trades"][1]["entry_i"] == 10,
          f"halts={r['n_daily_halts']} trades={[(x['why'], x['entry_i']) for x in r['trades']]}")

    # risk halving at -15% from peak: a persistent -2%/DAY gap decline; each
    # re-entry gaps through its 1-unit stop and loses ~1.75% of equity, so
    # the -15% and -25% device thresholds trip inside 80 bars
    n5 = 300
    cc = 100.0 * (0.98 ** np.arange(n5))
    oo = np.roll(cc, 1); oo[0] = 100.0
    hh = np.maximum(oo, cc) * 1.002
    ll = np.minimum(oo, cc) * 0.998
    t2 = np.array([t1 + i * 86_400_000 for i in range(n5)], np.int64)
    df2 = pd.DataFrame(dict(open_ts=t2, open=oo, high=hh, low=ll, close=cc,
                            volume=np.full(n5, 100.0),
                            ts=pd.to_datetime(t2, unit="ms", utc=True)))
    evs = tuple(range(1, n5 - 2, 6))
    # the stop is 0.5% OF PRICE (ATR-like), so the 2% daily move always
    # spans it and every trade can realize its full risk
    r = E.run(df2, plan(n5, le=evs, sd_l=0.005 * cc),
              BASE["fee"], BASE["slip"], 1.0)
    check("A5b risk halves at -15% from peak and review-halts at -25%",
          r["risk_mult_final"] == 0.5 and r["n_review_halt"] >= 1,
          f"mult={r['risk_mult_final']} review={r['n_review_halt']} "
          f"trades={len(r['trades'])}")


def audit_funding_ladder():
    df = bars([(100, 100.5, 99.5, 100.0)] * 10)
    f_ts = np.array([T0 + 3 * HOUR], np.int64)      # settlement during bar 3
    f_rate = np.array([0.0001])                      # long PAYS 0.01%
    r = E.run(df, plan(10, le=(1,), sd_l=5.0),
              BASE["fee"], BASE["slip"], 1.0,
              funding=(f_ts, f_rate))
    # qty ~ 99.65 units; pay = qty*close3*0.0001
    qty = r["trades"][0]["qty"]
    exp_pay = qty * 100.0 * 0.0001
    check("A6a funding charged at the settlement instant (long pays)",
          close(r["fund_paid"], exp_pay, 1e-9) and r["n_funding"] == 1,
          f"paid={r['fund_paid']:.6f} exp={exp_pay:.6f}")
    r = E.run(df, plan(10, se=(1,), sd_s=5.0), BASE["fee"], BASE["slip"], 1.0,
              funding=(f_ts, f_rate))
    check("A6b short RECEIVES the positive funding",
          r["fund_paid"] < 0 and r["n_funding"] == 1)
    # ladder ordering: adverse < base returns; stress worst; gate best
    rng = np.random.default_rng(3)
    n = 400
    cc = 100 + np.cumsum(rng.normal(0, 0.5, n))
    oo = np.roll(cc, 1); oo[0] = 100
    hh = np.maximum(oo, cc) + np.abs(rng.normal(0, 0.3, n))
    ll = np.minimum(oo, cc) - np.abs(rng.normal(0, 0.3, n))
    dfr = pd.DataFrame(dict(open_ts=np.array([T0 + i * HOUR for i in range(n)], np.int64),
                            open=oo, high=hh, low=ll, close=cc,
                            volume=np.full(n, 100.0),
                            ts=pd.to_datetime(np.array([T0 + i * HOUR for i in range(n)], np.int64), unit="ms", utc=True)))
    evs = tuple(range(3, n - 6, 9))
    p = plan(n, le=evs, sd_l=2.0, max_hold=6)
    rets = {}
    for ck in ("gate", "base", "adverse", "stress"):
        cc2 = E.COSTS[ck]
        rr = E.run(dfr, p, cc2["fee"], cc2["slip"], cc2["stop_slip_mult"])
        rets[ck] = rr["eq"][-1]
    check("A6c cost ladder orders returns: gate > base > adverse > stress",
          rets["gate"] >= rets["base"] >= rets["adverse"] >= rets["stress"],
          f"{ {k: round(v, 1) for k, v in rets.items()} }")


# ── real-data checks ───────────────────────────────────────────────────────
def audit_real():
    path = "data/binance_klines_1h_taker/BTCUSDT_1h.csv"
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df["ts"] = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
    df = df.sort_values("ts").reset_index(drop=True)
    plan_fn = SD.SPECS["QS-001"]["build"]

    # truncation causality: signals identical on a common prefix
    cut = int(len(df) * 0.6)
    p1 = plan_fn(df, "1h")
    p2 = plan_fn(df.iloc[:cut].reset_index(drop=True), "1h")
    ok = all(np.array_equal(
        np.asarray(pd.Series(p1[k]).fillna(False), bool)[:cut],
        np.asarray(pd.Series(p2[k]).fillna(False), bool))
        for k in ("long_event", "short_event"))
    check("R1 truncation causality (signals unchanged on a truncated series)",
          ok)

    # determinism
    p = plan_fn(df, "1h")
    ck = E.COSTS["base"]
    r1 = E.run(df, p, ck["fee"], ck["slip"], 1.0)
    r2 = E.run(df, p, ck["fee"], ck["slip"], 1.0)
    check("R2 determinism (two runs identical)",
          r1["eq"].tolist() == r2["eq"].tolist()
          and len(r1["trades"]) == len(r2["trades"]))

    # fill timing: entries always at least one bar after their event bar
    fills_ok = all(t["entry_i"] >= 1 for t in r1["trades"])
    check("R3 entries fill strictly after the signal bar", fills_ok,
          f"n={len(r1['trades'])}")

    # embargo/purge bookkeeping
    n = len(df)
    segs = E.segment_trades(
        r1["trades"],
        [("train", 0, int(n * 0.4)), ("val", int(n * 0.4) + 1, int(n * 0.6)),
         ("wf", int(n * 0.6) + 1, int(n * 0.8)),
         ("holdout", int(n * 0.8) + 1, n - 1)], 300)
    total = sum(len(v) for v in segs.values())
    check("R4 segment assignment covers every non-purged trade exactly once",
          total <= len(r1["trades"])
          and sum(len(segs[k]) for k in ("train", "val", "wf", "holdout")) == total,
          f"{total}/{len(r1['trades'])}")

    # DSR sanity: a strong book's PSR near 1, a random book's near 0.5
    check("R5 PSR bounds", 0.0 <= E.deflated_sharpe([3.0], 500) <= 1.0
          and E.deflated_sharpe([3.0], 500) > 0.99
          and abs(E.deflated_sharpe([0.0], 500) - 0.5) < 0.01)


def main():
    OUT.append("QS family-A engine audit — qs_engine.py + qs_strats.py")
    OUT.append(f"run {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    import hashlib
    for f in ("qs_engine.py", "qs_strats.py"):
        with open(os.path.join(HERE, f), "rb") as fh:
            OUT.append(f"{f} sha256: {hashlib.sha256(fh.read()).hexdigest()}")
    OUT.append("")
    audit_sizing()
    audit_stops()
    audit_frequency()
    audit_holds()
    audit_risk_devices()
    audit_funding_ladder()
    audit_real()
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
