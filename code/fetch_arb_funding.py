#!/usr/bin/env python
"""Fetch the full Binance USDT-M funding history for ARBUSDT.

Same purpose and format as `fetch_jup_funding.py` (the "funding lesson" in
AGENTS.md): every perpetual result must charge funding at the settlement
instants, and ARB had NO funding file on disk -- `data/binance_funding/`
carried BTC/ETH/SOL/SUI/XRP/HYPE/SPX/JUP only. A cbpackf run on ARB without
this file would silently charge no carry.

Public REST only, no keys. Output format matches the existing files:
    [{"t": <fundingTime ms>, "r": <rate>, "T": <fundingTime ms>}, ...]

Usage: python code/fetch_arb_funding.py
"""
import json
import os
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYMBOL = "ARBUSDT"
OUT = os.path.join(ROOT, "data", "binance_funding", f"{SYMBOL}_funding.json")
BASE = "https://fapi.binance.com/fapi/v1/fundingRate"
# ARB's perp was onboarded 2023-03-23 (Binance exchangeInfo onboardDate
# 1679554800000). Start before it so no early settlement is missed.
START_MS = 1677000000000
END_MS = int(time.time() * 1000)


def page(start: int) -> list:
    url = f"{BASE}?symbol={SYMBOL}&limit=1000&startTime={start}&endTime={END_MS}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())


def main() -> int:
    rows, cursor = [], START_MS
    while True:
        batch = page(cursor)
        if not batch:
            break
        rows.extend(batch)
        nxt = int(batch[-1]["fundingTime"]) + 1
        if nxt <= cursor:
            break
        cursor = nxt
        if len(batch) < 1000:
            break
        time.sleep(0.25)

    seen, out = set(), []
    for b in rows:
        t = int(b["fundingTime"])
        if t in seen:
            continue
        seen.add(t)
        out.append({"t": t, "r": float(b["fundingRate"]), "T": t})
    out.sort(key=lambda x: x["t"])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f)
    if out:
        print(f"wrote {len(out)} settlements to {OUT}")
        print("first", time.strftime("%Y-%m-%d %H:%M", time.gmtime(out[0]["t"] / 1000)),
              "last", time.strftime("%Y-%m-%d %H:%M", time.gmtime(out[-1]["t"] / 1000)))
        gaps = [out[i + 1]["t"] - out[i]["t"] for i in range(len(out) - 1)]
        odd = sum(1 for g in gaps if g > 9 * 3600 * 1000)
        print(f"max gap {max(gaps)/3600000:.2f} h, gaps>9h: {odd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
