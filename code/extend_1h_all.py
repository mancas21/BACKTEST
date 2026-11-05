import os, time, requests, csv

OUT = r"C:\Users\Lenovo\AppData\Local\Temp\opencode\binance_klines_1h"
BASE = "https://fapi.binance.com"
SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "SUIUSDT", "HYPEUSDT", "SPXUSDT", "XRPUSDT"]
LIMIT = 1000
END = int(time.time() * 1000)

def extend(s):
    path = os.path.join(OUT, s + "_1h.csv")
    old = list(csv.DictReader(open(path)))
    have = {int(r["open_ts"]) for r in old}
    last = max(have)
    rows, st, sess = [], last + 3600000, requests.Session()
    while st <= END:
        r = sess.get(BASE + "/fapi/v1/klines",
                     params={"symbol": s, "interval": "1h", "limit": LIMIT, "startTime": st},
                     timeout=30)
        if r.status_code != 200:
            print(s, "HTTP", r.status_code, r.text[:150])
            break
        d = r.json()
        if not d:
            break
        for x in d:
            if int(x[0]) > last and int(x[0]) <= END and int(x[0]) not in have:
                rows.append(x)
                have.add(int(x[0]))
        st = d[-1][0] + 3600000
        if len(d) < LIMIT:
            break
        time.sleep(0.15)
    with open(path, "a", newline="") as f:
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
