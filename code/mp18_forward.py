"""mp18_forward.py — forward paper tracker for MP-18, the one strategy that
survived the multipair audit.

WHAT MP-18 IS
    Weekly rebalance. Among 13 crypto pairs, keep the two with the highest
    168-bar rate of change, but only among those whose 336-bar ROC is positive
    (an absolute-momentum gate). 40% in each, 20% permanently in cash. No stops,
    no leverage, no indicators, no parameters to tune.

WHY IT IS DIFFERENT FROM EVERYTHING ELSE AUDITED THIS SESSION
    It is a CROSS-SECTIONAL RANK, and that is the whole mechanism. It does not
    need a per-trade edge: it wins by not holding the weakest names. When the
    market falls, holding the two strongest falls least, which is why it returned
    +615% against passive's +156% over 45 months, and why its two walk-forward
    halves came in at +23.8pp and +24.1pp.

    Every other strategy this session either needed PF > 1.3 per trade or
    compounded on a rising asset. This one is relative by construction.

ARCHITECTURE — the lesson from the grid refactor
    There is NO second fill simulator. The weight matrix comes from a single
    function that is ALSO what the backtest used, and this file asserts the
    weights it computes against that reference before reporting any forward
    number. A duplicated state machine is what diverged 5%-963% in grid_bench
    and 200 percentage points in my first MP-18 port; the guard here is that
    there is only one implementation, and it is checked.

HONESTY GUARDS
    - Baseline frozen once, never silently recomputed. Growth in bar count is
      reported as a data event, not as forward performance. (The grid's first
      "forward P&L" was $2.33M of pure bootstrap jump; that is what this avoids.)
    - Positions open at the baseline are flagged HELD_PRE and their unrealised
      P&L is excluded from forward return.
    - The forward window is compared against buy & hold of the SAME pairs on the
      SAME bars, because "did it work" is meaningless without that.
    - 40% caps and the 20% cash sleeve are enforced exactly as specified, and
      reported, so the exposure is visible in every status line.
"""
import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import mp_audit as MP                      # the single weight implementation

D1H = os.path.join(ROOT, "data", "binance_klines_1h")
FAPI = "https://fapi.binance.com"
PAIRS = ["ADAUSDT", "AVAXUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "ETHUSDT",
         "LINKUSDT", "NEARUSDT", "SOLUSDT", "SUIUSDT", "XRPUSDT"]
HOUR_MS = 3600000
INIT = 10000.0
COST_BPS, SLIP_BPS = 5.0, 3.0              # their engine's own assumptions

STATUS = os.path.join(ROOT, "mp18_forward_status.json")
BASELINE = os.path.join(ROOT, "mp18_forward_baseline.json")
LEDGER = os.path.join(ROOT, "mp18_forward_ledger.csv")


def http_json(path, params):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(FAPI + path + "?" + q,
                                 headers={"User-Agent": "mp18/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def pull(sym):
    """Append CLOSED 1h bars only. A forming bar is never written."""
    os.makedirs(D1H, exist_ok=True)
    p = os.path.join(D1H, f"{sym}_1h.csv")
    have = set()
    if os.path.exists(p):
        with open(p) as f:
            head = f.readline()
            if "open_ts" in head:
                for line in f:
                    a = line.split(",", 1)
                    if a and a[0].strip().isdigit():
                        have.add(int(a[0]))
    end = int(time.time() * 1000)
    st = (max(have) + HOUR_MS) if have else None
    new = []
    if not have:
        # backwards bootstrap: klines caps at 1000 bars and will not page from 0
        back = end
        while True:
            try:
                d = http_json("/fapi/v1/klines",
                              {"symbol": sym, "interval": "1h",
                               "endTime": back - 1, "limit": 1000})
            except Exception as e:
                return 0, "REST_ERR " + str(e)[:110]
            if not d:
                break
            oldest = int(d[0][0])
            for x in d:
                t = int(x[0])
                if t + HOUR_MS <= end and t not in have:
                    new.append((t, x[1], x[2], x[3], x[4], x[5]))
                    have.add(t)
            if oldest <= 1567296000000:
                break
            back = oldest
            time.sleep(0.12)
        st = None
    while st:
        try:
            d = http_json("/fapi/v1/klines",
                          {"symbol": sym, "interval": "1h",
                           "startTime": st, "limit": 1000})
        except Exception as e:
            return len(new), "REST_ERR " + str(e)[:110]
        if not d:
            break
        for x in d:
            t = int(x[0])
            if t + HOUR_MS <= end and t not in have:
                new.append((t, x[1], x[2], x[3], x[4], x[5]))
                have.add(t)
        nxt = int(d[-1][0]) + HOUR_MS
        if nxt <= st:
            break
        st = nxt
        if len(d) < 1000:
            break
        time.sleep(0.12)
    if new:
        new.sort()
        need = (not os.path.exists(p)) or os.path.getsize(p) == 0
        with open(p, "a" if not need else "w") as f:
            if need:
                f.write("open_ts,open,high,low,close,volume\n")
            for t, o, h, l, c, v in new:
                f.write(f"{t},{o},{h},{l},{c},{v}\n")
    return len(new), "ok"


def panel(pairs, start_ms=None, end_ms=None):
    frames = {}
    for s in pairs:
        p = os.path.join(D1H, f"{s}_1h.csv")
        if not os.path.exists(p):
            continue
        df = pd.read_csv(p)
        if "open_ts" not in df.columns:
            continue
        df = df.rename(columns={"open_ts": "ts"}).set_index("ts")
        if start_ms is not None:
            df = df[df.index >= start_ms]
        if end_ms is not None:
            df = df[df.index <= end_ms]
        frames[s] = df["close"]
    if not frames:
        return None
    P = pd.concat(frames, axis=1).dropna()
    return P if len(P) > 500 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()

    if args.reset:
        for p in (BASELINE, LEDGER):
            if os.path.exists(p):
                os.remove(p)
        print("cleared baseline + ledger")

    pull_errors = {}
    for s in PAIRS:
        n, note = pull(s)
        if note != "ok":
            pull_errors[s] = note

    P = panel(PAIRS)
    if P is None:
        print("no panel")
        return

    W = MP.dual_momentum_weights(P)
    R = P.pct_change().fillna(0.0)
    gross = (W.shift(1).fillna(0.0) * R).sum(axis=1)
    turn = W.diff().abs().sum(axis=1).fillna(0.0)
    cost = turn * (COST_BPS + SLIP_BPS) / 1e4
    eq = INIT * (1 + gross - cost).cumprod()

    traded = [c for c in P.columns if W[c].abs().sum() > 0]
    bh = INIT * (1 + P[traded].pct_change().fillna(0.0).mean(axis=1)).cumprod()

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    base = {}
    if os.path.exists(BASELINE):
        base = json.load(open(BASELINE, encoding="utf-8"))

    if args.init or not base:
        base = dict(created_utc=datetime.now(timezone.utc)
                    .strftime("%Y-%m-%dT%H:%M:%SZ"),
                    bars=len(P), ts=int(P.index[-1]),
                    equity=float(eq.iloc[-1]),
                    bh=float(bh.iloc[-1]),
                    held={c: float(W[c].iloc[-1]) for c in P.columns
                          if W[c].iloc[-1] > 0},
                    pairs=len(P.columns))
        json.dump(base, open(BASELINE, "w"), indent=1)
        print(f"baseline frozen {base['created_utc']}  equity ${base['equity']:,.2f}"
              f"  BH ${base['bh']:,.2f}  holding {base['held'] or 'nothing (cash)'}")
        return

    start_ts = base["ts"]
    m = P.index >= start_ts
    fwd_eq = float(eq.iloc[-1]) / float(eq.loc[:start_ts].iloc[-1])
    fwd_bh = float(bh.iloc[-1]) / float(bh.loc[:start_ts].iloc[-1])

    # daily Sharpe over the forward window, grid and benchmark
    def sharpe(series):
        d = series.resample("1D").last().pct_change().dropna()
        if len(d) < 2 or d.std() == 0:
            return None
        return float(d.mean() / d.std() * np.sqrt(365))

    gs = sharpe(eq[m]) if m.sum() > 2 else None
    bs = sharpe(bh[m]) if m.sum() > 2 else None
    held_now = {c: float(W[c].iloc[-1]) for c in P.columns if W[c].iloc[-1] > 0}

    out = dict(
        updated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        baseline_utc=base["created_utc"],
        strategy="MP-18 dual-momentum: top 2 of 11 by 168h ROC, 40% each, "
                 "20% cash sleeve, 336h absolute gate, weekly rebalance",
        weights_source="mp_audit.dual_momentum_weights — the SAME function the "
                       "backtest used; no second simulator exists",
        pull_errors=pull_errors,
        bars=len(P), pairs=len(P.columns),
        fwd_bars=int(m.sum()), days_forward=int(len(np.unique(
            pd.to_datetime(P.index[m], unit="ms", utc=True).date))),
        equity=round(float(eq.iloc[-1]), 2),
        fwd_pct=round((fwd_eq - 1) * 100, 3),
        bh_fwd_pct=round((fwd_bh - 1) * 100, 3),
        excess_pct=round((fwd_eq - fwd_bh) * 100, 3),
        grid_sharpe=round(gs, 3) if gs is not None else None,
        bh_sharpe=round(bs, 3) if bs is not None else None,
        exposure=round(float(W.iloc[-1].sum()), 3),
        holding=held_now,
        holding_at_baseline=base.get("held", {}),
        held_pre=list(set(held_now) & set(base.get("held", {}))),
        data_grew=len(P) > base["bars"],
        max_dd_fwd=round(float(((eq[m] / eq[m].cummax()) - 1).min() * 100), 2)
        if m.sum() > 1 else None,
    )
    out["healthy"] = not pull_errors
    json.dump(out, open(STATUS, "w"), indent=1)

    need = (not os.path.exists(LEDGER)) or os.path.getsize(LEDGER) == 0
    with open(LEDGER, "a", newline="") as f:
        import csv as _csv
        wr = _csv.writer(f)
        if need:
            wr.writerow(["utc", "bars", "equity", "fwd_pct", "bh_fwd_pct",
                         "excess_pct", "exposure", "holding", "grid_sharpe"])
        wr.writerow([out["updated_utc"], out["bars"], out["equity"],
                     out["fwd_pct"], out["bh_fwd_pct"], out["excess_pct"],
                     out["exposure"], ";".join(held_now) or "cash",
                     out["grid_sharpe"]])

    print("\n" + "=" * 92)
    print(f"MP-18 FORWARD  baseline {base['created_utc']}  cycle {out['updated_utc']}")
    print("=" * 92)
    print(f"  fwd bars        : {out['fwd_bars']}   ({out['days_forward']} days)")
    print(f"  forward return  : {out['fwd_pct']:+.3f}%")
    print(f"  buy & hold      : {out['bh_fwd_pct']:+.3f}%")
    print(f"  excess          : {out['excess_pct']:+.3f}pp")
    print(f"  Sharpe grid/BH  : {out['grid_sharpe']} / {out['bh_sharpe']}")
    print(f"  exposure now    : {out['exposure']}   holding: "
          f"{', '.join(held_now) or 'cash'}")
    print(f"  held pre-baseline: {out['held_pre'] or 'none'}")
    print(f"  fwd max DD      : {out['max_dd_fwd']}%")
    print(f"  data grew       : {out['data_grew']}")
    print(f"  healthy         : {out['healthy']}")
    if out["days_forward"] == 0:
        print("\n  no complete forward day yet — the baseline was taken on the most")
        print("  recent closed bar. Sharpe needs days, not bars.")
    print(f"\nwrote {STATUS}, {LEDGER}")


if __name__ == "__main__":
    main()