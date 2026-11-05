"""fetch_5m_taker.py — 5m Binance futures klines WITH the taker-flow fields.

WHY THESE COLUMNS
    Binance's kline endpoint returns 12 fields but my existing CSVs kept only 6.
    Field 9 (`taker_buy_base_volume`) is the aggressive-buy volume -- REAL order
    flow, the only non-proxy flow measure obtainable from REST. Strategies S05
    (taker-flow imbalance) and S06 (CVD divergence) in the QUANT CRYPTO BOT 10
    pack depend on it, so without it those two cannot be tested at all rather
    than tested badly.

    S05 is also the pack's own standout: in its synthetic matrix, flow and
    autocorrelation-regime were the only two effects that stayed tradable after
    taker costs. So the honest test of this pack is mostly a test of S05.

FIELDS
    0 open_time  1 open  2 high  3 low  4 close  5 volume  6 close_time
    7 quote_vol  8 trades  9 taker_buy_base  10 taker_buy_quote  11 ignore
"""
import argparse
import json
import os
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "binance_klines_5m_taker")
FAPI = "https://fapi.binance.com"
SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "SUIUSDT"]
HDR = "open_ts,open,high,low,close,volume,taker_buy_base,taker_buy_quote,n_trades"


def get(sym, start, end, limit=1500, tries=5):
    q = urllib.parse.urlencode({"symbol": sym, "interval": "5m",
                                "startTime": start, "endTime": end, "limit": limit})
    url = FAPI + "/fapi/v1/klines?" + q
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "f5t/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            if k == tries - 1:
                raise
            time.sleep(1.5 * (k + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sym", default=None)
    ap.add_argument("--days", type=int, default=730)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    syms = [a.sym] if a.sym else SYMS
    end = int(time.time() * 1000)
    start = end - a.days * 86400 * 1000

    for sym in syms:
        path = os.path.join(OUT, f"{sym}_5m.csv")
        rows = {}
        st = start
        calls = 0
        while st < end:
            d = get(sym, st, end)
            if not d:
                break
            for x in d:
                t = int(x[0])
                rows[t] = (float(x[1]), float(x[2]), float(x[3]), float(x[4]),
                           float(x[5]), float(x[9]), float(x[10]), float(x[8]))
            last = int(d[-1][0])
            calls += 1
            if last <= st:
                break
            st = last + 300000
            if calls % 25 == 0:
                print(f"  {sym}: {len(rows):,} bars...", flush=True)
            time.sleep(0.12)
        ts = sorted(rows)
        with open(path, "w", encoding="utf-8") as f:
            f.write(HDR + "\n")
            for t in ts:
                o, h, l, c, v, tb, tq, n = rows[t]
                f.write(f"{t},{o},{h},{l},{c},{v},{tb},{tq},{n}\n")
        # verify coverage in DAYS, not by file existence (a partial file must not
        # be mistaken for a complete one)
        span_d = (ts[-1] - ts[0]) / 86400000 if ts else 0
        print(f"{sym}: {len(ts):,} bars, {span_d:.1f} days, {calls} calls -> {path}",
              flush=True)


if __name__ == "__main__":
    main()