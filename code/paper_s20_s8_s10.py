#!/usr/bin/env python
"""paper_s20_s8_s10.py — paper tracker for S20, S8, S10 (1h, 11 symbols)."""
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
STATUS = os.path.join(ROOT, "paper_s20_s8_s10_status.json")
BASELINE = os.path.join(ROOT, "paper_s20_s8_s10_baseline.json")
LEDGER = os.path.join(ROOT, "paper_s20_s8_s10_ledger.csv")
D1H = os.path.join(DATA, "binance_klines_1h")


def http_json(path, params):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(FAPI + path + "?" + q, headers={"User-Agent": "paper/1.0"})
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


def weights_s8(P):
    """S8: FundingMom — rank by ROC, filter by funding."""
    # Need funding data — approximate with price momentum only for now
    # Funding filter: skip longs with funding > threshold, shorts with funding < -threshold
    # Without live funding, use momentum-only ranking
    roc = P / P.shift(168) - 1
    roc336 = P / P.shift(336) - 1
    W = pd.DataFrame(0.0, index=P.index, columns=P.columns)
    for i in range(336, len(P)):
        r168 = roc.iloc[i]
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
    # Rebalance every 168 bars
    W_rebal = pd.DataFrame(0.0, index=P.index, columns=P.columns)
    last_w = pd.Series(0.0, index=P.columns)
    for i in range(len(P)):
        if i >= 336 and (i == 336 or i % 168 == 0):
            last_w = W.iloc[i].copy()
        W_rebal.iloc[i] = last_w
    return W_rebal


def weights_s10(P):
    """S10: SharpeMom — rank by ROC/vol, gate by 336-bar ROC."""
    roc168 = P / P.shift(168) - 1
    vol168 = P.pct_change().rolling(168, min_periods=168).std(ddof=0)
    score = roc168 / vol168
    roc336 = P / P.shift(336) - 1
    W = pd.DataFrame(0.0, index=P.index, columns=P.columns)
    for i in range(336, len(P)):
        sc = score.iloc[i]
        r336 = roc336.iloc[i]
        valid = sc.notna() & r336.notna()
        if not valid.any():
            continue
        long_cands = [s for s in P.columns if valid[s] and r336[s] > 0]
        short_cands = [s for s in P.columns if valid[s] and r336[s] < 0]
        if len(long_cands) < 2 or len(short_cands) < 2:
            continue
        long_ranked = sorted(long_cands, key=lambda s: sc[s], reverse=True)
        short_ranked = sorted(short_cands, key=lambda s: sc[s])
        for s in long_ranked[:2]:
            W.iloc[i, W.columns.get_loc(s)] = 0.25
        for s in short_ranked[:2]:
            W.iloc[i, W.columns.get_loc(s)] = -0.25
    W_rebal = pd.DataFrame(0.0, index=P.index, columns=P.columns)
    last_w = pd.Series(0.0, index=P.columns)
    for i in range(len(P)):
        if i >= 336 and (i == 336 or i % 168 == 0):
            last_w = W.iloc[i].copy()
        W_rebal.iloc[i] = last_w
    return W_rebal


def weights_s20(P):
    """S20: Composite — z(ROC/vol) - z(funding). Without funding, use z(ROC/vol)."""
    roc168 = P / P.shift(168) - 1
    vol168 = P.pct_change().rolling(168, min_periods=168).std(ddof=0)
    score = roc168 / vol168
    roc336 = P / P.shift(336) - 1
    W = pd.DataFrame(0.0, index=P.index, columns=P.columns)
    for i in range(336, len(P)):
        sc = score.iloc[i]
        r336 = roc336.iloc[i]
        valid = sc.notna() & r336.notna()
        if not valid.any():
            continue
        # z-score across symbols
        vals = sc[valid]
        sm = vals.mean()
        ss = vals.std(ddof=0)
        if ss == 0:
            continue
        z_sc = (sc - sm) / ss
        long_cands = [s for s in P.columns if valid[s] and r336[s] > 0]
        short_cands = [s for s in P.columns if valid[s] and r336[s] < 0]
        if len(long_cands) < 2 or len(short_cands) < 2:
            continue
        long_ranked = sorted(long_cands, key=lambda s: z_sc[s], reverse=True)
        short_ranked = sorted(short_cands, key=lambda s: z_sc[s])
        for s in long_ranked[:2]:
            W.iloc[i, W.columns.get_loc(s)] = 0.25
        for s in short_ranked[:2]:
            W.iloc[i, W.columns.get_loc(s)] = -0.25
    W_rebal = pd.DataFrame(0.0, index=P.index, columns=P.columns)
    last_w = pd.Series(0.0, index=P.columns)
    for i in range(len(P)):
        if i >= 336 and (i == 336 or i % 168 == 0):
            last_w = W.iloc[i].copy()
        W_rebal.iloc[i] = last_w
    return W_rebal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()

    if args.reset:
        for p in (BASELINE, LEDGER, STATUS):
            if os.path.exists(p):
                os.remove(p)
        print("cleared")

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

    # Compute weights for each strategy
    W8 = weights_s8(P)
    W10 = weights_s10(P)
    W20 = weights_s20(P)
    R = P.pct_change().fillna(0.0)

    # Backtest each
    results = {}
    for name, W in [("S8", W8), ("S10", W10), ("S20", W20)]:
        gross = (W.shift(1).fillna(0.0) * R).sum(axis=1)
        turn = W.diff().abs().sum(axis=1).fillna(0.0)
        cost = turn * (COST_BPS + SLIP_BPS) / 1e4
        eq = INIT * (1 + gross - cost).cumprod()
        traded = [c for c in P.columns if W[c].abs().sum() > 0]
        bh = INIT * (1 + P[traded].pct_change().fillna(0.0).mean(axis=1)).cumprod()
        results[name] = dict(W=W, eq=eq, bh=bh, traded=traded)

    base = {}
    if os.path.exists(BASELINE):
        base = json.load(open(BASELINE, encoding="utf-8"))

    if args.init or not base:
        base = dict(created_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    bars=len(P), ts=int(P.index[-1].timestamp() * 1000),
                    equity={n: round(float(results[n]["eq"].iloc[-1]), 2) for n in results},
                    bh=round(float(results["S20"]["bh"].iloc[-1]), 2),
                    held={n: {c: float(results[n]["W"][c].iloc[-1]) for c in P.columns if abs(results[n]["W"][c].iloc[-1]) > 0} for n in results},
                    pairs=len(P.columns))
        json.dump(base, open(BASELINE, "w"), indent=1)
        print(f"baseline frozen {base['created_utc']}")
        for n in results:
            print(f"  {n}: equity ${results[n]['eq'].iloc[-1]:,.2f}  holding {base['held'][n] or 'cash'}")
        return

    start_ts = pd.Timestamp(base["ts"], unit="ms", tz="UTC")
    out = dict(updated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               baseline_utc=base["created_utc"],
               pull_errors=pull_errors, bars=len(P), pairs=len(P.columns))

    for name in results:
        eq = results[name]["eq"]
        bh = results[name]["bh"]
        W = results[name]["W"]
        m = P.index >= start_ts
        fwd_eq = float(eq.iloc[-1]) / float(eq.loc[:start_ts].iloc[-1]) if m.sum() > 0 else 1.0
        fwd_bh = float(bh.iloc[-1]) / float(bh.loc[:start_ts].iloc[-1]) if m.sum() > 0 else 1.0
        held_now = {c: float(W[c].iloc[-1]) for c in P.columns if abs(W[c].iloc[-1]) > 0}
        out[name] = dict(
            equity=round(float(eq.iloc[-1]), 2),
            fwd_pct=round((fwd_eq - 1) * 100, 3),
            bh_fwd_pct=round((fwd_bh - 1) * 100, 3),
            excess_pct=round((fwd_eq - fwd_bh) * 100, 3),
            exposure=round(float(W.iloc[-1].abs().sum()), 3),
            holding=held_now,
            fwd_bars=int(m.sum()),
            max_dd_fwd=round(float(((eq[m] / eq[m].cummax()) - 1).min() * 100), 2) if m.sum() > 1 else None,
        )

    out["healthy"] = not pull_errors
    json.dump(out, open(STATUS, "w"), indent=1)

    # Ledger
    need = (not os.path.exists(LEDGER)) or os.path.getsize(LEDGER) == 0
    with open(LEDGER, "a", newline="") as f:
        wr = csv.writer(f)
        if need:
            wr.writerow(["utc", "bars", "S8_eq", "S8_fwd", "S10_eq", "S10_fwd", "S20_eq", "S20_fwd", "S8_hold", "S10_hold", "S20_hold"])
        wr.writerow([out["updated_utc"], out["bars"],
                     out["S8"]["equity"], out["S8"]["fwd_pct"],
                     out["S10"]["equity"], out["S10"]["fwd_pct"],
                     out["S20"]["equity"], out["S20"]["fwd_pct"],
                     ";".join(f"{k}:{v}" for k, v in out["S8"]["holding"].items()) or "cash",
                     ";".join(f"{k}:{v}" for k, v in out["S10"]["holding"].items()) or "cash",
                     ";".join(f"{k}:{v}" for k, v in out["S20"]["holding"].items()) or "cash"])

    print("\n" + "=" * 92)
    print(f"PAPER S20/S8/S10  baseline {base['created_utc']}  cycle {out['updated_utc']}")
    print("=" * 92)
    for name in ["S20", "S8", "S10"]:
        d = out[name]
        print(f"  {name}: equity ${d['equity']:,.2f}  fwd {d['fwd_pct']:+.3f}%  excess {d['excess_pct']:+.3f}pp  holding: {', '.join(f'{k}={v}' for k,v in d['holding'].items()) or 'cash'}")
    print(f"  healthy: {out['healthy']}")
    print(f"\nwrote {STATUS}, {LEDGER}")


if __name__ == "__main__":
    main()
