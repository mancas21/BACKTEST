#!/usr/bin/env python
"""mp18_v2_paper.py — paper trading tracker for MP-18 v2 (market-neutral, vectorized)."""
from __future__ import annotations
import argparse, csv, json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CODE = os.path.join(ROOT, "code")
sys.path.insert(0, CODE)

PAIRS = ["ADAUSDT","AVAXUSDT","BNBUSDT","BTCUSDT","DOGEUSDT","ETHUSDT",
         "LINKUSDT","NEARUSDT","SOLUSDT","SUIUSDT","XRPUSDT"]
FAPI = "https://fapi.binance.com"
HOUR_MS = 3600000
INIT = 10000.0
COST_BPS, SLIP_BPS = 5.0, 3.0
LOOKBACK = 168
ABS_GATE = 336
REBAL_BARS = 336

STATUS = os.path.join(ROOT, "mp18_v2_paper_status.json")
BASELINE = os.path.join(ROOT, "mp18_v2_paper_baseline.json")
LEDGER = os.path.join(ROOT, "mp18_v2_paper_ledger.csv")
D1H = os.path.join(DATA, "binance_klines_1h")


def http_json(path, params):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(FAPI + path + "?" + q, headers={"User-Agent": "mp18v2/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def pull(sym):
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
        back = end
        while True:
            try:
                d = http_json("/fapi/v1/klines", {"symbol": sym, "interval": "1h",
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
            d = http_json("/fapi/v1/klines", {"symbol": sym, "interval": "1h",
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
        if len(d) < 1000:
            break
        st = int(d[-1][0]) + HOUR_MS
        time.sleep(0.12)
    if new:
        mode = "a" if os.path.exists(p) else "w"
        with open(p, mode, newline="") as f:
            w = csv.writer(f)
            if mode == "w":
                w.writerow(["open_ts", "open", "high", "low", "close", "volume"])
            for row in sorted(new):
                w.writerow(row)
    return len(new), "ok"


def panel(pairs):
    frames = {}
    for sym in pairs:
        p = os.path.join(D1H, f"{sym}_1h.csv")
        if not os.path.exists(p):
            return None
        d = pd.read_csv(p)
        d.columns = [c.strip().lower() for c in d.columns]
        d["ts"] = pd.to_datetime(d["open_ts"], unit="ms", utc=True)
        d = d.sort_values("ts").reset_index(drop=True)
        frames[sym] = d.set_index("ts")["close"]
    P = pd.DataFrame(frames)
    P = P.dropna(how="all")
    return P


def mp18_v2_weights(P):
    """Market-neutral: long top-2, short bottom-2 by 168-bar ROC. Vectorized."""
    roc168 = P / P.shift(LOOKBACK) - 1
    roc336 = P / P.shift(ABS_GATE) - 1

    W = pd.DataFrame(0.0, index=P.index, columns=P.columns)

    for i in range(ABS_GATE, len(P)):
        r168 = roc168.iloc[i]
        r336 = roc336.iloc[i]
        valid = r168.notna() & r336.notna()
        if not valid.any():
            continue
        long_cands = [s for s in P.columns if valid[s] and r336[s] > 0]
        short_cands = [s for s in P.columns if valid[s] and r336[s] < 0]
        if not long_cands or not short_cands:
            continue
        long_ranked = sorted(long_cands, key=lambda s: r168[s], reverse=True)
        short_ranked = sorted(short_cands, key=lambda s: r168[s])
        for s in long_ranked[:2]:
            W.iloc[i, W.columns.get_loc(s)] = 0.25
        for s in short_ranked[:2]:
            W.iloc[i, W.columns.get_loc(s)] = -0.25

    # Rebalance every REBAL_BARS: hold weights between rebalances
    W_rebal = pd.DataFrame(0.0, index=P.index, columns=P.columns)
    last_w = pd.Series(0.0, index=P.columns)
    for i in range(len(P)):
        if i >= ABS_GATE and (i == ABS_GATE or i % REBAL_BARS == 0):
            last_w = W.iloc[i].copy()
        W_rebal.iloc[i] = last_w
    return W_rebal


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
        print(f"  pulled {s}: {n} new bars, {note}")

    P = panel(PAIRS)
    if P is None:
        print("no panel")
        return
    print(f"Panel: {P.shape}, {P.index[0]} to {P.index[-1]}")

    W = mp18_v2_weights(P)
    R = P.pct_change().fillna(0.0)
    gross = (W.shift(1).fillna(0.0) * R).sum(axis=1)
    turn = W.diff().abs().sum(axis=1).fillna(0.0)
    cost = turn * (COST_BPS + SLIP_BPS) / 1e4
    eq = INIT * (1 + gross - cost).cumprod()

    traded = [c for c in P.columns if W[c].abs().sum() > 0]
    bh = INIT * (1 + P[traded].pct_change().fillna(0.0).mean(axis=1)).cumprod()

    base = {}
    if os.path.exists(BASELINE):
        base = json.load(open(BASELINE, encoding="utf-8"))

    if args.init or not base:
        base = dict(created_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    bars=len(P), ts=int(P.index[-1].timestamp() * 1000),
                    equity=float(eq.iloc[-1]),
                    bh=float(bh.iloc[-1]),
                    held={c: float(W[c].iloc[-1]) for c in P.columns if abs(W[c].iloc[-1]) > 0},
                    pairs=len(P.columns))
        json.dump(base, open(BASELINE, "w"), indent=1)
        print(f"baseline frozen {base['created_utc']}  equity ${base['equity']:,.2f}"
              f"  BH ${base['bh']:,.2f}  holding {base['held'] or 'nothing (cash)'}")
        return

    start_ts = pd.Timestamp(base["ts"], unit="ms", tz="UTC")
    m = P.index >= start_ts
    fwd_eq = float(eq.iloc[-1]) / float(eq.loc[:start_ts].iloc[-1]) if m.sum() > 0 else 1.0
    fwd_bh = float(bh.iloc[-1]) / float(bh.loc[:start_ts].iloc[-1]) if m.sum() > 0 else 1.0

    def sharpe(series):
        d = series.resample("1D").last().pct_change().dropna()
        if len(d) < 2 or d.std() == 0:
            return None
        return float(d.mean() / d.std() * np.sqrt(365))

    gs = sharpe(eq[m]) if m.sum() > 2 else None
    bs = sharpe(bh[m]) if m.sum() > 2 else None
    held_now = {c: float(W[c].iloc[-1]) for c in P.columns if abs(W[c].iloc[-1]) > 0}

    out = dict(
        updated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        baseline_utc=base["created_utc"],
        strategy="MP-18 v2: market-neutral long top-2/short bottom-2 by 168h ROC, "
                 "336h absolute gate, bi-weekly rebalance",
        weights_source="mp18_v2_paper.mp18_v2_weights — same function as backtest",
        pull_errors=pull_errors,
        bars=len(P), pairs=len(P.columns),
        fwd_bars=int(m.sum()),
        days_forward=int(len(np.unique(pd.to_datetime(P.index[m]).date))) if m.sum() > 0 else 0,
        equity=round(float(eq.iloc[-1]), 2),
        fwd_pct=round((fwd_eq - 1) * 100, 3),
        bh_fwd_pct=round((fwd_bh - 1) * 100, 3),
        excess_pct=round((fwd_eq - fwd_bh) * 100, 3),
        grid_sharpe=round(gs, 3) if gs is not None else None,
        bh_sharpe=round(bs, 3) if bs is not None else None,
        exposure=round(float(W.iloc[-1].abs().sum()), 3),
        holding=held_now,
        holding_at_baseline=base.get("held", {}),
        held_pre=list(set(held_now) & set(base.get("held", {}))),
        data_grew=len(P) > base["bars"],
        max_dd_fwd=round(float(((eq[m] / eq[m].cummax()) - 1).min() * 100), 2) if m.sum() > 1 else None,
    )
    out["healthy"] = not pull_errors
    json.dump(out, open(STATUS, "w"), indent=1)

    need = (not os.path.exists(LEDGER)) or os.path.getsize(LEDGER) == 0
    with open(LEDGER, "a", newline="") as f:
        wr = csv.writer(f)
        if need:
            wr.writerow(["utc", "bars", "equity", "fwd_pct", "bh_fwd_pct",
                         "excess_pct", "exposure", "holding", "grid_sharpe"])
        wr.writerow([out["updated_utc"], out["bars"], out["equity"],
                     out["fwd_pct"], out["bh_fwd_pct"], out["excess_pct"],
                     out["exposure"], ";".join(f"{k}:{v}" for k, v in held_now.items()) or "cash",
                     out["grid_sharpe"]])

    print("\n" + "=" * 92)
    print(f"MP-18 v2 PAPER  baseline {base['created_utc']}  cycle {out['updated_utc']}")
    print("=" * 92)
    print(f"  fwd bars        : {out['fwd_bars']}   ({out['days_forward']} days)")
    print(f"  forward return  : {out['fwd_pct']:+.3f}%")
    print(f"  buy & hold      : {out['bh_fwd_pct']:+.3f}%")
    print(f"  excess          : {out['excess_pct']:+.3f}pp")
    print(f"  Sharpe grid/BH  : {out['grid_sharpe']} / {out['bh_sharpe']}")
    print(f"  exposure now    : {out['exposure']}   holding: "
          f"{', '.join(f'{k}={v}' for k, v in held_now.items()) or 'cash'}")
    print(f"  fwd max DD      : {out['max_dd_fwd']}%")
    print(f"  healthy         : {out['healthy']}")
    print(f"\nwrote {STATUS}, {LEDGER}")


if __name__ == "__main__":
    main()
