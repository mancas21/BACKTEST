#!/usr/bin/env python
r"""Fill the eight contracts the ML4T crypto-perps-funding universe declares
that this repo had never downloaded: AAVE, APT, ATOM, COMP, DOT, INJ, MKR, UNI.

Why: the case study's universe is nineteen perpetual pairs
(`case_studies/crypto_perps_funding/config/setup.yaml`). The store carried 11 of
them with BOTH klines and funding. The missing eight are all mid-cap alts -- the
names whose funding goes most extreme, i.e. the short leg the mechanism lives
on. A backtest on the surviving 11 would not measure the published strategy.

Source: Binance USD-M public REST (`fapi/v1/klines`, `fapi/v1/fundingRate`),
no keys. Append-only and idempotent: merges by timestamp, rewrites sorted, and
never deletes a row already on disk. The kline CSV keeps the store's exact
schema (`open_ts,open,high,low,close,volume`); the funding JSON keeps its
`[{"t","r","T"}]` schema.

Usage: python code/fetch_ml4t_universe.py
"""
from __future__ import annotations

import csv
import json
import os
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KDIR = os.path.join(ROOT, "data", "binance_klines_1h")
FDIR = os.path.join(ROOT, "data", "binance_funding")
BASE = "https://fapi.binance.com"
SYMBOLS = ["AAVEUSDT", "APTUSDT", "ATOMUSDT", "COMPUSDT",
           "DOTUSDT", "INJUSDT", "MKRUSDT", "UNIUSDT"]
LIMIT = 1000


def get(path: str, params: dict) -> list:
    for attempt in range(5):
        r = requests.get(BASE + path, params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (418, 429):
            wait = 2 ** attempt * 5
            print(f"    throttled {r.status_code}, sleeping {wait}s", flush=True)
            time.sleep(wait)
            continue
        raise RuntimeError(f"{path} {params} -> HTTP {r.status_code} {r.text[:200]}")
    raise RuntimeError(f"{path} {params} -> gave up after throttling")


def fetch_klines(sym: str) -> int:
    path = os.path.join(KDIR, f"{sym}_1h.csv")
    rows: dict[int, tuple] = {}
    if os.path.exists(path):
        with open(path, newline="") as f:
            rdr = csv.reader(f)
            hdr = next(rdr, None)
            if hdr and hdr[0] != "open_ts":
                raise RuntimeError(f"{path}: unexpected header {hdr}")
            for row in rdr:
                if row:
                    rows[int(row[0])] = (row[0], row[1], row[2], row[3], row[4], row[5])
    n0 = len(rows)
    cursor = 0
    while True:
        batch = get("/fapi/v1/klines", {"symbol": sym, "interval": "1h",
                                        "limit": LIMIT, "startTime": cursor})
        if not batch:
            break
        for x in batch:
            t = int(x[0])
            if t not in rows:
                rows[t] = (str(t), x[1], x[2], x[3], x[4], x[5])
        cursor = int(batch[-1][0]) + 3_600_000
        if len(batch) < LIMIT:
            break
        time.sleep(0.12)
    out = [rows[t] for t in sorted(rows)]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["open_ts", "open", "high", "low", "close", "volume"])
        w.writerows(out)
    return len(out) - n0


def fetch_funding(sym: str) -> int:
    path = os.path.join(FDIR, f"{sym}_funding.json")
    rows: dict[int, dict] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for rec in json.load(f):
                rows[int(rec["t"])] = {"t": int(rec["t"]), "r": float(rec["r"]),
                                       "T": int(rec.get("T", rec["t"]))}
    n0 = len(rows)
    # The funding endpoint caps a page at 500 records and treats startTime=0 as
    # "unset" (returning the LATEST page instead of the first), so paginate from
    # a real epoch and stop only on an EMPTY page. Measured 2026-11-22.
    cursor = 1_577_836_800_000          # 2020-01-01T00:00Z
    for _ in range(200):
        batch = get("/fapi/v1/fundingRate", {"symbol": sym, "limit": LIMIT,
                                             "startTime": cursor})
        if not batch:
            break
        for b in batch:
            t = int(b["fundingTime"])
            if t not in rows:
                rows[t] = {"t": t, "r": float(b["fundingRate"]), "T": t}
        nxt = int(batch[-1]["fundingTime"]) + 1
        if nxt <= cursor:
            break
        cursor = nxt
        time.sleep(0.12)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([rows[t] for t in sorted(rows)], f)
    return len(rows) - n0


def main() -> int:
    os.makedirs(KDIR, exist_ok=True)
    os.makedirs(FDIR, exist_ok=True)
    for sym in SYMBOLS:
        nk = fetch_klines(sym)
        time.sleep(0.15)
        nf = fetch_funding(sym)
        time.sleep(0.15)
        print(f"{sym:<10} klines +{nk:<6} funding +{nf:<5}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
