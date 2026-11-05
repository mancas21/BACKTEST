#!/usr/bin/env python
"""Extend data/binance_funding/*.json to the current settlement.

Why this exists: the funding lesson in AGENTS.md — "A partially-funded
backtest is a different backtest". The klines were extended on 2026-10-27 but
five of the eight funding files still ended 2026-10-01, so any run after that
date charged NO funding for the tail (measured: XRPUSDT 15m klines reached
2026-10-27 20:45 while XRPUSDT_funding.json ended 2026-10-22 08:00).

Append-only: keeps every existing byte, appends only settlements after each
file's last t, same {"t","r","T"} schema. Public REST only, no keys.
"""
import json
import os
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "data", "binance_funding")
BASE = "https://fapi.binance.com/fapi/v1/fundingRate"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "SUIUSDT", "HYPEUSDT",
           "XRPUSDT", "SPXUSDT"]  # JUPUSDT already current (2026-10-27)


def page(symbol: str, start: int) -> list:
    end = int(time.time() * 1000)
    url = f"{BASE}?symbol={symbol}&limit=1000&startTime={start}&endTime={end}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())


def extend(symbol: str) -> None:
    path = os.path.join(DIR, f"{symbol}_funding.json")
    rows = json.load(open(path, encoding="utf-8"))
    last_t = max(int(r["t"]) for r in rows)
    new, cursor = [], last_t + 1
    while True:
        batch = page(symbol, cursor)
        if not batch:
            break
        for b in batch:
            row = {"t": int(b["fundingTime"]), "r": float(b["fundingRate"]),
                   "T": int(b["fundingTime"])}
            if row["t"] > last_t:
                new.append(row)
        nxt = int(batch[-1]["fundingTime"]) + 1
        if nxt <= cursor:
            break
        cursor = nxt
        if len(batch) < 1000:
            break
    if not new:
        print(f"{symbol:10s} already current (last {last_t})")
        return
    rows.extend(new)
    rows.sort(key=lambda r: r["t"])
    json.dump(rows, open(path, "w", encoding="utf-8"))
    last_new = max(r["t"] for r in new)
    print(f"{symbol:10s} +{len(new)} settlements -> last {last_new}")


if __name__ == "__main__":
    for s in SYMBOLS:
        extend(s)
