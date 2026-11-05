"""fetch_1h_pairs.py — top up the 1h archive so the multipair audit is not run
on a 7-pair intersection when the real universe is 11.

The audit needs a common clock across every pair. Building that clock by
intersecting whatever happens to be on disk silently shrinks the universe: only
7 of the 11 pairs had 1h files, and the intersection started 2023-05-03 rather
than covering the pairs' real history. A strategy that trades the top 2 by
momentum behaves differently on 7 names than on 11, so the missing pairs have
to exist before the result means anything.
"""
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
D1H = os.path.join(ROOT, "data", "binance_klines_1h")
FAPI = "https://fapi.binance.com"
SPOT = "https://api.binance.com"
PAIRS = ["ADAUSDT", "NEARUSDT", "DOGEUSDT", "BNBUSDT", "AVAXUSDT", "LINKUSDT",
         "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "SUIUSDT"]


def get(base, path, params):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(base + path + "?" + q,
                                 headers={"User-Agent": "fetch1h/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def load_existing(path):
    ts = set()
    if not os.path.exists(path):
        return ts
    with open(path) as f:
        head = f.readline()
        if "open_ts" not in head:
            return ts
        for line in f:
            a = line.split(",", 1)
            if a and a[0].strip().isdigit():
                ts.add(int(a[0]))
    return ts


def fetch(sym, path):
    have = load_existing(path)
    end = int(time.time() * 1000)
    st = (max(have) + 3600000) if have else None
    new = []
    pages = 0

    # Backwards bootstrap. klines returns at most 1000 bars per call and will
    # not page from 0, so a fresh file only ever got the most recent 999 bars --
    # which would then COLLAPSE the multi-pair intersection to ~41 days and make
    # the momentum ranking meaningless. Walk back from now instead.
    if not have:
        back = end
        bp = 0
        while bp < 300:
            params = {"symbol": sym, "interval": "1h", "endTime": back - 1,
                      "limit": 1000}
            try:
                raw = get(FAPI, "/fapi/v1/klines", params)
            except Exception:
                try:
                    raw = get(SPOT, "/api/v3/klines", params)
                except Exception as e:
                    return len(new), "BOTH_ERR " + str(e)[:90]
            import json as _json
            d = _json.loads(raw)
            if not d:
                break
            bp += 1
            oldest = int(d[0][0])
            for x in d:
                t = int(x[0])
                if t + 3600000 > end:
                    continue
                if t not in have:
                    new.append((t, x[1], x[2], x[3], x[4], x[5]))
                    have.add(t)
            if oldest <= 1567296000000:      # USDT-M launch
                break
            back = oldest
            time.sleep(0.12)
        st = None

    while st and pages < 300:
        params = {"symbol": sym, "interval": "1h", "limit": 1000}
        if st:
            params["startTime"] = st
        try:
            raw = get(FAPI, "/fapi/v1/klines", params)
        except Exception as e:
            if st is None:
                # futures listing may not exist; try spot
                try:
                    raw = get(SPOT, "/api/v3/klines", params)
                except Exception as e2:
                    return len(new), "BOTH_ERR " + str(e2)[:90]
            else:
                return len(new), "REST_ERR " + str(e)[:90]
        import json
        d = json.loads(raw)
        if not d:
            break
        pages += 1
        for x in d:
            t = int(x[0])
            if t + 3600000 > end:
                continue
            if t not in have:
                new.append((t, x[1], x[2], x[3], x[4], x[5]))
                have.add(t)
        if len(d) < 1000:
            break
        nxt = int(d[-1][0]) + 3600000
        if st and nxt <= st:
            break
        st = nxt
        time.sleep(0.12)
    if new:
        new.sort()
        need = (not os.path.exists(path)) or os.path.getsize(path) == 0
        with open(path, "a" if not need else "w") as f:
            if need:
                f.write("open_ts,open,high,low,close,volume\n")
            for t, o, h, l, c, v in new:
                f.write(f"{t},{o},{h},{l},{c},{v}\n")
    return len(new), "ok"


def main():
    os.makedirs(D1H, exist_ok=True)
    for sym in PAIRS:
        p = os.path.join(D1H, f"{sym}_1h.csv")
        n, note = fetch(sym, p)
        tot = len(load_existing(p))
        print(f"  {sym:<9} +{n:>6,} new  total {tot:>7,}  {note}", flush=True)


if __name__ == "__main__":
    main()