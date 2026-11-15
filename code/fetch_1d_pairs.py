#!/usr/bin/env python
"""Fetch 1d klines for the 2026-only top-100 campaign + funding coverage.

Campaign contract (user request, 2026-11-14): the top-100 strategies
(results/top100_2026-11-09_strategies.json) re-run at tf=1d on
JUP/HYPE/SUI/ARB/SOL/ETH/NVDA/SPCX/1000PEPE/XRP/BTC with ONLY year-2026
data. "Only 2026" is enforced at the BYTES: every 1d file starts at
2026-01-01T00:00Z, so no engine can ever see pre-2026 bars. Warmup comes
out of the window itself (declared in the campaign report).

Files written (new dirs, nothing overwritten):
  data/binance_klines_1d/<SYM>_1d.csv        6-col  (open_ts,o,h,l,c,v)
  data/binance_klines_1d_taker/<SYM>_1d.csv  9-col  (+taker_buy_base,taker_buy_quote,n_trades)
  data/binance_funding/<SYM>_funding.json    created for the 3 symbols that
                                             had none; existing files for the
                                             campaign symbols are EXTENDED
                                             append-only to the current
                                             settlement (funding lesson:
                                             a partially-funded backtest is
                                             a different backtest).

Public REST only, no keys. Column orders replicate the existing repo files
exactly (checked against data/binance_klines_1h and _1h_taker).
"""
import json
import os
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
FAPI = "https://fapi.binance.com"

# 2026-01-01T00:00:00Z in ms — the campaign window's first byte.
START_MS = 1767225600000

SYMBOLS = ["JUPUSDT", "HYPEUSDT", "SUIUSDT", "ARBUSDT", "SOLUSDT",
           "ETHUSDT", "NVDAUSDT", "SPCXUSDT", "1000PEPEUSDT", "XRPUSDT",
           "BTCUSDT"]

# Funding files that already exist on disk (extend append-only).
HAVE_FUNDING = ["ARBUSDT", "BTCUSDT", "ETHUSDT", "HYPEUSDT", "JUPUSDT",
                "SOLUSDT", "SPXUSDT", "SUIUSDT", "XRPUSDT"]
# The three campaign symbols with NO funding file yet (create from listing).
NEW_FUNDING = ["NVDAUSDT", "SPCXUSDT", "1000PEPEUSDT"]


def get(url: str, tries: int = 5):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "f5t/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(2 ** k)
    return []


def fetch_klines(sym: str, interval: str, start: int) -> list:
    out, cur = [], start
    end = int(time.time() * 1000)
    while cur < end:
        q = urllib.parse.urlencode({"symbol": sym, "interval": interval,
                                    "startTime": cur, "endTime": end,
                                    "limit": 1500})
        rows = get(FAPI + "/fapi/v1/klines?" + q)
        if not rows:
            break
        out.extend(rows)
        cur = rows[-1][0] + 1
        if len(rows) < 1500:
            break
        time.sleep(0.3)
    return out


def write_klines(sym: str) -> int:
    rows = fetch_klines(sym, "1d", START_MS)
    # keep CLOSED daily bars only: the API's last row is today's partial
    # candle (close_time in the future) — repo kline files carry closed bars
    now = int(time.time() * 1000)
    rows = [r for r in rows if r[6] <= now]
    if not rows:
        raise SystemExit(f"{sym}: API returned no 1d klines")
    d_plain = os.path.join(DATA, "binance_klines_1d")
    d_taker = os.path.join(DATA, "binance_klines_1d_taker")
    os.makedirs(d_plain, exist_ok=True)
    os.makedirs(d_taker, exist_ok=True)
    # plain: 6 cols; taker: 9 cols in the repo's order
    # (open_ts,o,h,l,c,v,taker_buy_base,taker_buy_quote,n_trades).
    with open(os.path.join(d_plain, f"{sym}_1d.csv"), "w", newline="\n") as f:
        f.write("open_ts,open,high,low,close,volume\n")
        for r in rows:
            f.write(",".join(str(x) for x in
                             [r[0], r[1], r[2], r[3], r[4], r[5]]) + "\n")
    with open(os.path.join(d_taker, f"{sym}_1d.csv"), "w", newline="\n") as f:
        f.write("open_ts,open,high,low,close,volume,"
                "taker_buy_base,taker_buy_quote,n_trades\n")
        for r in rows:
            f.write(",".join(str(x) for x in
                             [r[0], r[1], r[2], r[3], r[4], r[5],
                              r[9], r[10], r[8]]) + "\n")
    return len(rows)


def funding_path(sym: str) -> str:
    return os.path.join(DATA, "binance_funding", f"{sym}_funding.json")


def page_funding(sym: str, start: int) -> list:
    end = int(time.time() * 1000)
    out, cur = [], start
    while cur < end:
        url = (f"{FAPI}/fapi/v1/fundingRate?symbol={sym}"
               f"&limit=1000&startTime={cur}&endTime={end}")
        rows = get(url)
        if not rows:
            break
        out.extend(rows)
        cur = rows[-1]["fundingTime"] + 1
        if len(rows) < 1000:
            break
        time.sleep(0.3)
    return out


def write_funding(sym: str, create: bool) -> int:
    """Append-only extension; for `create` symbols the file starts at
    listing (the API's own first record). Schema matches the existing
    files: bare JSON list of {"t","r","T"}."""
    p = funding_path(sym)
    if os.path.exists(p):
        with open(p) as f:
            cur = json.load(f)
        last_t = cur[-1]["t"] if cur else 0
        rows = page_funding(sym, last_t + 1)
        new = [{"t": r["fundingTime"], "r": float(r["fundingRate"]),
                "T": r.get("fundingTime")} for r in rows]
        cur.extend(new)
        with open(p, "w") as f:
            json.dump(cur, f)
        return len(new)
    if not create:
        return -1
    rows = page_funding(sym, 0)
    recs = [{"t": r["fundingTime"], "r": float(r["fundingRate"]),
             "T": r.get("fundingTime")} for r in rows]
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(recs, f)
    return len(recs)


def main():
    for sym in SYMBOLS:
        n = write_klines(sym)
        print(f"klines {sym}: {n} bars")
    for sym in NEW_FUNDING:
        n = write_funding(sym, create=True)
        print(f"funding {sym}: created, {n} settlements")
    for sym in HAVE_FUNDING:
        n = write_funding(sym, create=False)
        print(f"funding {sym}: +{n} settlements appended")


if __name__ == "__main__":
    main()
