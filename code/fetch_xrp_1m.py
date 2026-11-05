import os, time, requests, csv

OUT = r"C:\Users\Lenovo\AppData\Local\Temp\opencode\binance_klines_1m"
BASE = "https://fapi.binance.com"
SYM = "XRPUSDT"
LIMIT = 1000
END = int(time.time() * 1000)
START = END - 94 * 24 * 3600 * 1000

rows, et, sess = [], END, requests.Session()
while True:
    r = sess.get(BASE + "/fapi/v1/klines",
                 params={"symbol": SYM, "interval": "1m", "limit": LIMIT, "endTime": et},
                 timeout=30)
    if r.status_code != 200:
        print(SYM, "HTTP", r.status_code, r.text[:150])
        break
    d = r.json()
    if not d:
        break
    rows = d + rows
    if d[0][0] <= START:
        break
    et = d[0][0] - 1
    time.sleep(0.12)
seen = {}
for x in rows:
    if int(x[0]) >= START:
        seen[int(x[0])] = x
ks = sorted(seen)
path = os.path.join(OUT, SYM + "_1m.csv")
with open(path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["open_ts", "open", "high", "low", "close", "volume"])
    for k in ks:
        x = seen[k]
        w.writerow([int(x[0]), x[1], x[2], x[3], x[4], x[5]])
print(SYM, len(ks), "bars", flush=True)
print("DONE")
