#!/usr/bin/env python
"""Fetch the FULL Binance USDT-M funding history for symbols missing a file.

Why: every perpetual result must charge funding at the real settlement
instants (AGENTS.md, "THE FUNDING LESSON"). `data/binance_funding/` covers the
majors, but a matrix over "all pairs" reaches symbols with no funding file; a
backtest that cannot see the funding column silently overstates a hold-to-exit
book. This script fills the gap for every symbol that has kline data and no
funding file. Public REST only, no keys.

Output format matches the existing files:
    [{"t": <fundingTime ms>, "r": <rate>, "T": <fundingTime ms>}, ...]

Usage:
    python code/fetch_funding_missing.py            # only the missing ones
    python code/fetch_funding_missing.py --force    # re-fetch everything
    python code/fetch_funding_missing.py --symbols ADAUSDT,DOGEUSDT
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUND = os.path.join(ROOT, "data", "binance_funding")
BASE = "https://fapi.binance.com/fapi/v1/fundingRate"
START_MS = 1567296000000  # 2019-09-01, before the first USD-M perp funding
END_MS = int(time.time() * 1000)


def universe() -> set[str]:
    syms: set[str] = set()
    for d in glob.glob(os.path.join(ROOT, "data", "binance_klines*")):
        if not os.path.isdir(d):
            continue
        for f in glob.glob(os.path.join(d, "*.csv")):
            b = os.path.basename(f)[:-4]
            parts = b.split("_")
            syms.add(parts[0])
    return {s for s in syms if s.endswith("USDT")}


def page(sym: str, start: int) -> list:
    url = (f"{BASE}?symbol={sym}&limit=1000&startTime={start}"
           f"&endTime={END_MS}")
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 400:
            return []
        raise


def fetch(sym: str) -> list[dict]:
    rows, cursor = [], START_MS
    while True:
        batch = page(sym, cursor)
        if not isinstance(batch, list) or not batch:
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
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    have = {os.path.basename(f).split("_")[0]
            for f in glob.glob(os.path.join(FUND, "*.json"))}
    if a.symbols:
        want = [s.strip().upper() for s in a.symbols.split(",") if s.strip()]
    else:
        want = sorted(universe() - have)
    if not a.force:
        want = [s for s in want if s not in have]

    print(f"fetching {len(want)} symbols: {', '.join(want) or '(none)'}")
    ok, empty, failed = [], [], []
    for sym in want:
        try:
            rows = fetch(sym)
        except Exception as e:  # network / symbol not a perp
            failed.append((sym, f"{type(e).__name__}: {e}"))
            print(f"{sym:16} FAIL {type(e).__name__}")
            continue
        if not rows:
            empty.append(sym)
            print(f"{sym:16} EMPTY (not a USD-M perp or no settlements)")
            continue
        os.makedirs(FUND, exist_ok=True)
        path = os.path.join(FUND, f"{sym}_funding.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f)
        gaps = [rows[i + 1]["t"] - rows[i]["t"] for i in range(len(rows) - 1)]
        odd = sum(1 for g in gaps if g > 9 * 3600 * 1000)
        first = time.strftime("%Y-%m-%d", time.gmtime(rows[0]["t"] / 1000))
        last = time.strftime("%Y-%m-%d", time.gmtime(rows[-1]["t"] / 1000))
        print(f"{sym:16} OK  n={len(rows):5} {first}..{last} "
              f"maxgap={max(gaps)/3600000:.2f}h gaps>9h={odd}")
        ok.append(sym)

    print(f"\nwrote {len(ok)} funding files")
    if empty:
        print("EMPTY:", ", ".join(empty))
    if failed:
        for s, e in failed:
            print("FAILED:", s, e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
