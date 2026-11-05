"""Yahoo Finance pulls for equities/futures F0 — keyless v8 chart API.
Usage:
  python yahoo_fetcher.py SPY 1h      # ETF hourly (paged 700d windows)
  python yahoo_fetcher.py "ES=F" 1d   # futures daily full history
  python yahoo_fetcher.py ALL         # SPY QQQ ES=F NQ=F MES=F MNQ=F (1d + 1h)
Output: data/etf/<SYM>_<tf>.csv / data/futures/<SYM>_<tf>.csv
Cols: open_ts(ms UTC, bar OPEN),open,high,low,close,volume[,adjclose|adjfactor]
- daily ETFs carry adjclose; hourly ETFs carry adjfactor from daily div/split
  series (cumprod, applied backward from last bar).
- futures =F are continuous front-month (liquidity roll, NOT back-adjusted).
  Roll gaps stay in the data; engines must neutralize roll bars (see SESSIONS.md).
- idempotent: appends only bars newer than local max(open_ts).
"""
import sys
import os
import time
import json
import urllib.request

BASE = r"C:\Users\Lenovo\Documents\backtest-system\data"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"}
ETF = {"SPY": "etf", "QQQ": "etf"}
FUT = {"ES=F": "ES", "NQ=F": "NQ", "MES=F": "MES", "MNQ=F": "MNQ"}


def get(url, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except Exception as e:
            if "429" in str(e) and k < tries - 1:
                time.sleep(15 * (k + 1))
                continue
            raise


def fetch(sym, interval, p1, p2):
    u = (f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
         f"?interval={interval}&period1={p1}&period2={p2}&events=div%2Csplit")
    j = get(u)
    res = (j.get("chart") or {}).get("result") or [None]
    return res[0]


def daily_rows(res):
    ts = res["timestamp"]
    q = res["indicators"]["quote"][0]
    adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose")
    out = []
    for i, t in enumerate(ts):
        if q["close"][i] is None:
            continue
        out.append((t * 1000, q["open"][i], q["high"][i], q["low"][i],
                    q["close"][i], q["volume"][i] or 0,
                    adj[i] if adj and adj[i] else q["close"][i]))
    return out


def hourly_rows(res):
    ts = res.get("timestamp") or []
    q = res["indicators"]["quote"][0]
    out = []
    for i, t in enumerate(ts):
        if q["close"][i] is None:
            continue
        out.append((t * 1000, q["open"][i], q["high"][i], q["low"][i],
                    q["close"][i], q["volume"][i] or 0))
    return out


def adj_factors(sym):
    now = int(time.time())
    res = fetch(sym, "1d", 0, now)
    rows = daily_rows(res)
    if not rows:
        return {}
    last_adj = rows[-1][6] / rows[-1][5] if rows[-1][5] else 1.0
    # factor per day so that close*factor = adjclose, normalized: last day = 1
    f = {}
    scale = rows[-1][6] / rows[-1][5] if rows[-1][5] else 1.0
    for t, o, h, l, c, v, a in rows:
        day = t // 86400000
        f[day] = (a / c) / scale if c else 1.0
    return f


def dest(sym, tf):
    sub = ETF.get(sym, "futures")
    name = ETF.get(sym, FUT.get(sym, sym))
    d = os.path.join(BASE, sub)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{name}_{tf}.csv")


def load_max(path, ncols):
    have = {}
    if os.path.exists(path):
        for ln in open(path):
            p = ln.strip().split(",")
            if len(p) >= ncols:
                try:
                    have[int(p[0])] = True
                except ValueError:
                    pass
    return have


def pull(sym, tf):
    now = int(time.time())
    path = dest(sym, tf)
    if tf == "1d":
        res = fetch(sym, "1d", 0, now)
        rows = daily_rows(res)
        have = load_max(path, 7)
        new = [r for r in rows if r[0] not in have]
        mode = "a" if have else "w"
        with open(path, mode) as f:
            for r in new:
                f.write(",".join(str(x) for x in r) + "\n")
        print(f"{sym} 1d: +{len(new)} total={len(have) + len(new)}", flush=True)
    else:
        have = load_max(path, 7 if sym in ETF else 6)
        start = 0 if not have else (max(have) // 1000 + 1)
        allrows = []
        p2 = now
        while True:
            p1 = max(start, p2 - 700 * 86400)
            res = fetch(sym, "1h", p1, p2)
            if not res:
                break
            allrows += hourly_rows(res)
            if p1 <= start or not (res.get("timestamp")):
                break
            p2 = res["timestamp"][0] - 1
            time.sleep(3)
        if sym in ETF:
            fac = adj_factors(sym)
            rows = [(t, o, h, l, c, v, fac.get((t // 1000) // 86400, 1.0))
                    for t, o, h, l, c, v in allrows if t not in have]
        else:
            rows = [r for r in allrows if r[0] not in have]
        rows.sort()
        mode = "a" if have else "w"
        with open(path, mode) as f:
            for r in rows:
                f.write(",".join(str(x) for x in r) + "\n")
        print(f"{sym} 1h: +{len(rows)} total={len(have) + len(rows)}", flush=True)
    time.sleep(3)


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "ALL"
    b = sys.argv[2] if len(sys.argv) > 2 else "both"
    syms = list(ETF) + list(FUT) if a == "ALL" else [a]
    for s in syms:
        tfs = ["1d", "1h"] if b == "both" else [b]
        for t in tfs:
            try:
                pull(s, t)
            except Exception as e:
                print(s, t, "ERROR", str(e)[:150], flush=True)
    print("DONE", flush=True)
