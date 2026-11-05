import os, time, requests, csv, datetime

OUT = r"C:\Users\Lenovo\AppData\Local\Temp\opencode\binance_klines_1h"
BASE = "https://fapi.binance.com"
JOBS = {"HYPEUSDT": 1733011200000, "SPXUSDT": 1698796800000}
LIMIT = 1000
END = int(time.time() * 1000)

def fetch(sym, start):
    rows, st, sess = [], start, requests.Session()
    while True:
        r = sess.get(BASE + "/fapi/v1/klines",
                     params={"symbol": sym, "interval": "1h", "limit": LIMIT, "startTime": st},
                     timeout=30)
        if r.status_code != 200:
            print(sym, "HTTP", r.status_code, r.text[:150])
            return
        d = r.json()
        if not d:
            break
        rows.extend(d)
        st = d[-1][0] + 1
        if d[-1][0] >= END - 3600000 or len(d) < LIMIT:
            break
        time.sleep(0.15)
    seen = {}
    for x in rows:
        seen[int(x[0])] = x
    ks = sorted(seen)
    path = os.path.join(OUT, sym + "_1h.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["open_ts", "open", "high", "low", "close", "volume"])
        for k in ks:
            x = seen[k]
            w.writerow([int(x[0]), x[1], x[2], x[3], x[4], x[5]])
    f0 = datetime.datetime.fromtimestamp(ks[0] / 1000, datetime.timezone.utc).strftime("%Y-%m-%d")
    f1 = datetime.datetime.fromtimestamp(ks[-1] / 1000, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    print(sym, len(ks), "bars", f0, "->", f1, flush=True)

for s, st in JOBS.items():
    try:
        fetch(s, st)
    except Exception as e:
        print(s, "ERROR", e)
print("DONE")
