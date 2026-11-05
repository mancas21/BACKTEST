#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_solusdc_1h.py — SOL/USDC spot 1h klines from Binance into the repo's
data convention (open_ts ms, open,high,low,close,volume), same schema as the
binance_klines files so every harness reader parses them unchanged.

    python code/fetch_solusdc_1h.py                # from 2026-04-01 to now
    python code/fetch_solusdc_1h.py --start 2026-04-01 --end 2026-10-29

SOL/USDC is a distinct market from SOL/USDT (different quote asset, different
book); the file lives beside the USDT archive under its own name and any
campaign built on it cites the sha256 this script prints and stores in
data/SOLUSDC_IMPORT.json. Re-fetching a window that grew rewrites the file and
stales artifacts built on it — the documented extension path.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "binance_klines_1h", "SOLUSDC_1h.csv")
MANIFEST = os.path.join(ROOT, "data", "SOLUSDC_IMPORT.json")
SPOT = "https://api.binance.com/api/v3/klines"


def get(params):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{SPOT}?{q}", headers={"User-Agent": "fetch-solusdc/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-04-01")
    ap.add_argument("--end", default="")
    a = ap.parse_args()
    start_ms = int(dt.datetime.fromisoformat(a.start + "T00:00:00+00:00").timestamp() * 1000)
    end_ms = (int(dt.datetime.fromisoformat(a.end + "T00:00:00+00:00").timestamp() * 1000)
              if a.end else int(time.time() * 1000))
    rows = []
    cursor = start_ms
    while cursor < end_ms:
        batch = get({"symbol": "SOLUSDC", "interval": "1h", "startTime": cursor,
                     "endTime": end_ms, "limit": 1000})
        if not batch:
            break
        rows.extend(batch)
        cursor = batch[-1][0] + 3600 * 1000
        if len(batch) < 1000:
            break
        time.sleep(0.2)
    rows.sort(key=lambda r: r[0])
    seen, uniq = set(), []
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0])
            uniq.append(r)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("open_ts,open,high,low,close,volume\n")
        for r in uniq:
            f.write(f"{r[0]},{r[1]},{r[2]},{r[3]},{r[4]},{r[5]}\n")
    h = hashlib.sha256()
    with open(OUT, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    manifest = {
        "schema": "solusdc-import/1",
        "fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": "Binance spot /api/v3/klines SOLUSDC 1h (public, no key)",
        "file": "data/binance_klines_1h/SOLUSDC_1h.csv",
        "sha256": h.hexdigest(), "bars": len(uniq),
        "first": dt.datetime.fromtimestamp(uniq[0][0] / 1000, dt.timezone.utc).isoformat(),
        "last": dt.datetime.fromtimestamp(uniq[-1][0] / 1000, dt.timezone.utc).isoformat(),
        "window": f"{a.start}..{a.end or 'now'}",
    }
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    print(f"SOLUSDC_1h: {len(uniq)} bars  {manifest['first']}..{manifest['last']}")
    print(f"sha256 {h.hexdigest()}")
    print(f"manifest -> {os.path.relpath(MANIFEST, ROOT)}")


if __name__ == "__main__":
    main()
