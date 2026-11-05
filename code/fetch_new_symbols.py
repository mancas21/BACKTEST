#!/usr/bin/env python
"""Fetch Binance futures klines for ARB, NVDA, SPCX at 5m/15m/1h."""
import argparse, json, os, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASE = os.path.join(ROOT, "data", "binance_klines_{}_taker" if False else "binance_klines_{}")
# We'll store in binance_klines_{tf} to match existing convention
FAPI = "https://fapi.binance.com"
SYMS = ["ARBUSDT", "NVDAUSDT", "SPCXUSDT"]
INTERVALS = ["5m", "15m", "1h"]
DAYS = 730

TF_MS = {"5m": 5*60*1000, "15m": 15*60*1000, "1h": 60*60*1000}

def get(sym, interval, start, end, limit=1500, tries=5):
    q = urllib.parse.urlencode({"symbol": sym, "interval": interval,
                                "startTime": start, "endTime": end, "limit": limit})
    url = FAPI + "/fapi/v1/klines?" + q
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "f5t/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            if k == tries-1: raise
            time.sleep(2**k)
    return []

def fetch(sym, interval):
    ms = TF_MS[interval]
    out_dir = os.path.join(ROOT, "data", f"binance_klines_{interval}")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{sym}_{interval}.csv")
    # check if already exists with enough data
    if os.path.exists(out_path):
        with open(out_path) as f:
            n = sum(1 for _ in f) - 1
        if n >= 9000:
            print(f"  {sym} {interval}: already have {n} bars, skip")
            return
    end = int(time.time() * 1000)
    start = end - DAYS * 24 * 60 * 60 * 1000
    rows = []
    cur = start
    while cur < end:
        batch = get(sym, interval, cur, end)
        if not batch:
            break
        for k in batch:
            rows.append((k[0], k[1], k[2], k[3], k[4], k[5]))
        cur = batch[-1][0] + ms
        time.sleep(0.25)
        if len(rows) % 5000 == 0:
            print(f"    {sym} {interval}: {len(rows)} bars...")
    # dedup
    seen = set()
    uniq = []
    for r in rows:
        if r[0] in seen: continue
        seen.add(r[0])
        uniq.append(r)
    uniq.sort()
    with open(out_path, "w") as f:
        f.write("open_ts,open,high,low,close,volume\n")
        for ts, o, h, l, c, v in uniq:
            f.write(f"{ts},{o},{h},{l},{c},{v}\n")
    print(f"  {sym} {interval}: wrote {len(uniq)} bars -> {out_path}")

if __name__ == "__main__":
    for sym in SYMS:
        for iv in INTERVALS:
            print(f"Fetching {sym} {iv}...")
            try:
                fetch(sym, iv)
            except Exception as e:
                print(f"  ERROR {sym} {iv}: {e}")