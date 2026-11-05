"""Fetch AVAXUSDT + LINKUSDT 1h (report universe: SOL BTC ETH AVAX LINK).
Writes to data/binance_klines_1h/ with a header, idempotent append.
Usage: python fetch_avax_link_1h.py
"""
import os
import time
import csv
import requests

OUT = r"C:\Users\Lenovo\Documents\backtest-system\data\binance_klines_1h"
BASE = "https://fapi.binance.com"
SYMS = ["AVAXUSDT", "LINKUSDT"]
LIMIT = 1000


def fetch(sym):
    path = os.path.join(OUT, sym + "_1h.csv")
    have = set()
    first = True
    if os.path.exists(path):
        with open(path, newline="") as f:
            rdr = csv.reader(f)
            hdr = next(rdr, None)
            if hdr and hdr[0] != "open_ts":
                first = False
            for row in rdr:
                if row:
                    try:
                        have.add(int(row[0]))
                    except ValueError:
                        pass
        first = False
    rows = []
    st = 0 if not have else max(have) + 3600000
    end = int(time.time() * 1000)
    sess = requests.Session()
    while st <= end:
        r = sess.get(BASE + "/fapi/v1/klines",
                     params={"symbol": sym, "interval": "1h", "limit": LIMIT, "startTime": st},
                     timeout=30)
        if r.status_code != 200:
            print(sym, "HTTP", r.status_code, r.text[:150], flush=True)
            break
        d = r.json()
        if not d:
            break
        for x in d:
            t = int(x[0])
            if t not in have:
                rows.append((t, x[1], x[2], x[3], x[4], x[5]))
                have.add(t)
        st = d[-1][0] + 3600000
        if len(d) < LIMIT:
            break
        time.sleep(0.15)
    rows.sort()
    mode = "w" if first else "a"
    with open(path, mode, newline="") as f:
        w = csv.writer(f)
        if first:
            w.writerow(["open_ts", "open", "high", "low", "close", "volume"])
        for x in rows:
            w.writerow(x)
    print(sym, "added", len(rows), flush=True)


for s in SYMS:
    try:
        fetch(s)
    except Exception as e:
        print(s, "ERROR", str(e)[:200], flush=True)
print("DONE")