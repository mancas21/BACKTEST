import os, time, requests, csv

OUT = r"C:\Users\Lenovo\Documents\backtest-system\data\binance_klines_1m"
BASE = "https://fapi.binance.com"
SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "SUIUSDT", "HYPEUSDT", "SPXUSDT", "XRPUSDT"]
LIMIT = 1000
END = int(time.time() * 1000)

def extend(s):
    path = os.path.join(OUT, s + "_1m.csv")
    have = {}
    if os.path.exists(path):
        for r in csv.DictReader(open(path)):
            have[int(r["open_ts"])] = True
    last = max(have) if have else 0
    rows, st, sess = [], (last + 60000) if have else (END - 94 * 24 * 3600 * 1000), requests.Session()
    while st <= END:
        r = sess.get(BASE + "/fapi/v1/klines",
                     params={"symbol": s, "interval": "1m", "limit": LIMIT, "startTime": st},
                     timeout=30)
        if r.status_code != 200:
            print(s, "HTTP", r.status_code, r.text[:120])
            break
        d = r.json()
        if not d:
            break
        for x in d:
            t = int(x[0])
            if t > last and t <= END and t not in have:
                rows.append(x)
                have[t] = True
        st = d[-1][0] + 60000
        if len(d) < LIMIT:
            break
        time.sleep(0.15)
    with open(path, "a" if have else "w", newline="") as f:
        w = csv.writer(f)
        for x in rows:
            w.writerow([int(x[0]), x[1], x[2], x[3], x[4], x[5]])
    print(s, "added", len(rows), flush=True)

for s in SYMS:
    try:
        extend(s)
    except Exception as e:
        print(s, "ERROR", e)
print("DONE")
