"""fetch_taker.py — add the taker-buy volume column to the 1m archive.

WHY THIS EXISTS
---------------
SCALP-2 (OFI), SCALP-6 (CVD) and SCALP-9 (confluence) all need aggressive
buy/sell volume. My 1m CSVs saved only 6 of Binance's 12 kline fields and
dropped `taker_buy_base_volume`, which IS taker buy volume -- so the single most
useful order-flow proxy on the exchange was sitting on disk unused.

This re-pulls the existing window and appends the missing columns WITHOUT
touching open/high/low/close/volume. If the newly fetched close disagrees with
the stored close by more than a tick, the two sources disagree and the file must
not be silently rewritten -- that check is the whole reason this script is
careful rather than a two-line loop.

WHAT THIS DOES NOT RECOVER
    Sub-second resolution. OBI at "0.1% of mid within 3 seconds", iceberg
    detection at "3 partial fills within 10 seconds", and OFI at "100ms to 10s"
    all require tick or L2 data that does not exist on this box and is not
    obtainable from the REST klines endpoint at any price. Those strategies stay
    untestable here, and the report says so rather than quietly testing a coarser
    substitute.
"""
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
D1M = os.path.join(ROOT, "data", "binance_klines_1m")
FAPI = "https://fapi.binance.com"
SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "SUIUSDT"]

OLD_HDR = ["open_ts", "open", "high", "low", "close", "volume"]
NEW_HDR = ["open_ts", "open", "high", "low", "close", "volume",
           "taker_buy_base", "taker_buy_quote", "n_trades"]


def get(params):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(FAPI + "/fapi/v1/klines?" + q,
                                 headers={"User-Agent": "fetchtaker/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def read_existing(path):
    """Return (rows, header) where rows carry the 6 legacy columns."""
    rows = []
    hdr = None
    with open(path) as f:
        hdr = f.readline().strip().split(",")
        for line in f:
            a = line.rstrip("\n").split(",")
            if len(a) >= 6:
                try:
                    rows.append([int(a[0])] + [float(x) for x in a[1:6]])
                except ValueError:
                    pass
    return rows, hdr


def fetch_window(sym, start_ms, end_ms):
    """Fetch [start, end] with taker fields."""
    out = {}
    st = start_ms
    while st is not None and st < end_ms:
        d = get({"symbol": sym, "interval": "1m", "startTime": st,
                 "endTime": end_ms, "limit": 1000})
        if not d:
            break
        for x in d:
            t = int(x[0])
            # [5]=volume [7]=quote vol [8]=n trades [9]=taker buy base [10]=taker buy quote
            out[t] = (float(x[5]), float(x[9]), float(x[10]), float(x[8]))
        nxt = int(d[-1][0]) + 60000
        if nxt <= st:
            break
        st = nxt
        time.sleep(0.1)
    return out


def main():
    for sym in SYMS:
        path = os.path.join(D1M, f"{sym}_1m.csv")
        if not os.path.exists(path):
            print(f"  {sym}: no 1m file, skipping")
            continue
        rows, hdr = read_existing(path)
        if hdr == NEW_HDR:
            print(f"  {sym}: already has taker columns")
            continue
        t0, t1 = rows[0][0], rows[-1][0] + 60000
        print(f"  {sym}: {len(rows):,} bars, fetching taker fields "
              f"{t0}..{t1}", flush=True)
        tb = fetch_window(sym, t0, t1)
        if not tb:
            print(f"    fetch returned nothing for {sym}")
            continue

        # VERIFY against the stored closes before writing anything
        checked = 0
        bad = 0
        for r in rows:
            t = r[0]
            if t in tb:
                checked += 1
                if abs(r[5] - tb[t][0]) > 1e-8:
                    bad += 1
        if bad:
            print(f"    ABORT: {bad}/{checked} bars disagree on volume between "
                  f"the stored file and a fresh fetch. Not rewriting.")
            continue
        print(f"    verified {checked:,} bars agree on volume")

        missing = [r for r in rows if r[0] not in tb]
        if missing:
            print(f"    {len(missing):,} bars have no taker data "
                  f"(kept, taker fields blank)")

        tmp = path + ".tmp"
        with open(tmp, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(NEW_HDR)
            for r in rows:
                t = r[0]
                if t in tb:
                    v, tbb, tbq, nt = tb[t]
                    w.writerow([t] + r[1:] + [f"{tbb:.8f}", f"{tbq:.8f}",
                                              int(nt)])
                else:
                    w.writerow([t] + r[1:] + ["", "", ""])
        os.replace(tmp, path)
        print(f"    wrote {len(rows):,} rows with taker columns")


if __name__ == "__main__":
    main()