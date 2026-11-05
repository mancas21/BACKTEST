"""fetch_taker_tf.py — klines WITH the taker-flow fields (kline field 9) at ANY interval.

WHY
    `fetch_5m_taker.py` proved two of the ten strategies (S05 taker-flow, S06 CVD
    divergence) need `taker_buy_base`, which every older CSV in data/ dropped. This
    is the same fetcher generalised to 1m / 15m / 1h so the cross-timeframe study
    can test all ten families everywhere instead of quietly running eight.

FIELDS
    0 open_time  1 open  2 high  3 low  4 close  5 volume  6 close_time
    7 quote_vol  8 trades  9 taker_buy_base  10 taker_buy_quote  11 ignore

RESUMABLE
    A 730-day 1m pull is ~700 calls/symbol. The file is appended in place and the
    next run resumes from the last stored timestamp, so an interrupted pull costs
    only the calls it had already made. Without that, one dropped socket throws
    away twenty minutes.

RATE LIMITS
    /fapi/v1/klines weighs 10 per call at limit=1500, and the futures budget is
    2400/min => ~240 calls/min. We sleep between calls and back off hard on 429.

USAGE
    python code/fetch_taker_tf.py --tf 1h
    python code/fetch_taker_tf.py --tf 1m --sym BTCUSDT --days 730
"""
import argparse
import json
import os
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAPI = "https://fapi.binance.com"
SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "SUIUSDT"]
HDR = "open_ts,open,high,low,close,volume,taker_buy_base,taker_buy_quote,n_trades"
MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000}


def get(sym, interval, start, end, limit=1500, tries=6):
    q = urllib.parse.urlencode({"symbol": sym, "interval": interval,
                                "startTime": start, "endTime": end, "limit": limit})
    url = FAPI + "/fapi/v1/klines?" + q
    delay = 1.5
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ftf/1.0"})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            # 429/418 = weight or IP ban window. Sleep it out; do not hammer.
            if e.code in (429, 418):
                w = getattr(e, "headers", {}).get("Retry-After")
                time.sleep(float(w) if w else delay * (k + 1) * 2)
                delay *= 2
                continue
            if k == tries - 1:
                raise
            time.sleep(delay * (k + 1))
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(delay * (k + 1))
    raise RuntimeError(f"exhausted retries for {sym} {interval}")


def pull(sym, interval, days, out_dir):
    step = MS[interval]
    path = os.path.join(out_dir, f"{sym}_{interval}.csv")
    rows = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            next(f, None)
            for line in f:
                p = line.split(",")
                if len(p) == 9:
                    rows[int(p[0])] = (p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8])
    end = int(time.time() * 1000) - step          # never fetch the still-open bar
    start = end - days * 86400_000
    st = max(start, max(rows) + step) if rows else start
    calls = 0
    if st >= end:
        return path, len(rows), 0
    while st < end:
        d = get(sym, interval, st, end)
        if not d:
            break
        for x in d:
            t = int(x[0])
            if t >= start and t < end:
                rows[t] = (f"{float(x[1]):g}", f"{float(x[2]):g}", f"{float(x[3]):g}",
                           f"{float(x[4]):g}", f"{float(x[5]):g}", f"{float(x[9]):g}",
                           f"{float(x[10]):g}", str(int(x[8])))
        last = int(d[-1][0])
        calls += 1
        if last <= st:
            break
        st = last + step
        if calls % 50 == 0:
            _dump(path, rows)
            span_d = (max(rows) - min(rows)) / 86400000 if rows else 0
            print(f"  {sym} {interval}: {len(rows):,} bars, {span_d:.0f}d, {calls} calls", flush=True)
        time.sleep(0.13)                          # ~235 calls/min, under the 240 budget
    _dump(path, rows)
    return path, len(rows), calls


def _dump(path, rows):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(HDR + "\n")
        for t in sorted(rows):
            f.write(f"{t}," + ",".join(rows[t]) + "\n")
    os.replace(tmp, path)                         # atomic: never leave a half CSV


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", required=True, choices=list(MS))
    ap.add_argument("--sym", default=None)
    ap.add_argument("--days", type=int, default=730)
    a = ap.parse_args()
    out = os.path.join(ROOT, "data", f"binance_klines_{a.tf}_taker")
    os.makedirs(out, exist_ok=True)
    for sym in ([a.sym] if a.sym else SYMS):
        t0 = time.time()
        path, n, calls = pull(sym, a.tf, a.days, out)
        span_d = (n and 0) or 0
        print(f"{sym} {a.tf}: {n:,} bars, {calls} calls, {time.time()-t0:.0f}s -> {path}", flush=True)


if __name__ == "__main__":
    main()