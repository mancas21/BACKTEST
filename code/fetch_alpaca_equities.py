#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_alpaca_equities.py — pull US-equity OHLCV from Alpaca into the repo's
data convention (REGLA 0: data lands as files whose bytes are hashed into every
future run_id; the API is only the source of the bytes).

    python code/fetch_alpaca_equities.py                    # SPY QQQ AAPL MSFT NVDA, 1Day
    python code/fetch_alpaca_equities.py --symbols TSLA --start 2019-01-01 --tf 1Day

What it pins (declared here, echoed into the manifest):
  * feed        = sip   (the consolidated tape; the iex feed carries IEX-only
                         volume -- a fraction of the market -- and is banned
                         for backtest data, same honesty class as partial
                         funding histories)
  * adjustment  = all   (splits AND dividends back-applied: the series is
                         continuous in today's price scale; split dates show
                         no jump. The datacheck asserts this on known splits.)
  * timeframe   = 1Day  (bar timestamp is 00:00 ET of the trading day, i.e.
                         04:00Z/05:00Z depending on DST -- stored as-is)
  * schema      = open_ts,open,high,low,close,volume,n_trades,vwap
                  (open_ts = epoch ms of the bar label, same convention as the
                  binance_klines files, so code/vrun.py `_read_input` parses
                  these files unchanged; n_trades/vwap are Alpaca extras kept
                  for the future cost model)

Credentials come from the same env file the alpaca MCP server uses (default
C:/Users/Lenovo/trading-engines/execution/.env, keys ALPACA_API_KEY /
ALPACA_SECRET_KEY, APCA_* accepted too). The script never prints a secret.

Re-running over the same window rewrites the files: if new days exist the
bytes change and any artifacts built on them go STALE -- the documented
extension path, identical to the binance klines.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUTDIR = os.path.join(DATA, "alpaca_1d")
MANIFEST = os.path.join(DATA, "ALPACA_EQUITIES_IMPORT.json")
CHECK = os.path.join(ROOT, "results", "alpaca_equities_datacheck.txt")

DEFAULT_ENVFILE = r"C:/Users/Lenovo/trading-engines/execution/.env"
BASE = "https://data.alpaca.markets/v2/stocks/bars"
UNIVERSE = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"]

# splits inside the default window, to prove adjustment=all (no jump expected)
KNOWN_SPLITS = {
    "AAPL": [("2020-08-31", 4.0)],          # 7:1 was 2014, before the window
    "NVDA": [("2024-06-10", 10.0), ("2021-07-20", 4.0)],
}
TF_ALIAS = {"1Day": "1d", "1Min": "1m", "1Hour": "1h"}
LINE = "-" * 100
CHK = []


def chk(label, ok, detail=""):
    if not ok:
        raise AssertionError(f"FAIL {label}: {detail}")
    CHK.append(f"PASS  {label}" + (f"   [{detail}]" if detail else ""))
    print(f"PASS  {label}" + (f"   [{detail}]" if detail else ""))


def load_keys(envfile):
    """Read ALPACA/APCA key names from the env file; NEVER return-or-print secrets."""
    vals = {}
    for p in (envfile,):
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="replace"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    vals[k.strip()] = v.strip().strip('"').strip("'")
    kid = (os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY")
           or vals.get("ALPACA_API_KEY") or vals.get("APCA_API_KEY_ID"))
    sec = (os.environ.get("APCA_API_SECRET_KEY") or os.environ.get("ALPACA_SECRET_KEY")
           or vals.get("ALPACA_SECRET_KEY") or vals.get("APCA_API_SECRET_KEY"))
    if not kid or not sec:
        raise SystemExit("no Alpaca data keys found (env or envfile); refusing to guess")
    print(f"keys: loaded from envfile {os.path.basename(envfile)} "
          f"(id {kid[:4]}...{len(kid)} chars, secret <{len(sec)} chars, not shown>)")
    return kid, sec


def fetch_symbol(kid, sec, sym, tf, start, end):
    """One symbol, all pages, ascending. Returns list of bar dicts."""
    bars = []
    token = None
    while True:
        q = {"symbols": sym, "timeframe": tf, "start": start, "limit": 10000,
             "adjustment": "all", "feed": "sip"}
        if end:
            q["end"] = end
        if token:
            q["page_token"] = token
        req = urllib.request.Request(BASE + "?" + urllib.parse.urlencode(q),
                                     headers={"APCA-API-KEY-ID": kid,
                                              "APCA-API-SECRET-KEY": sec})
        with urllib.request.urlopen(req, timeout=60) as r:
            payload = json.loads(r.read().decode())
        chunk = (payload.get("bars") or {}).get(sym) or []
        bars.extend(chunk)
        token = payload.get("next_page_token")
        if not token:
            break
        time.sleep(0.15)
    return bars


def write_csv(path, bars):
    rows = []
    for b in bars:
        t = b["t"].replace("Z", "+00:00")
        ms = int(dt.datetime.fromisoformat(t).timestamp() * 1000)
        rows.append((ms, b["o"], b["h"], b["l"], b["c"], b["v"], b.get("n", 0), b.get("vw")))
    rows.sort(key=lambda r: r[0])
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("open_ts,open,high,low,close,volume,n_trades,vwap\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")
    return rows


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default=",".join(UNIVERSE))
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default="")
    ap.add_argument("--tf", default="1Day")
    ap.add_argument("--envfile", default=DEFAULT_ENVFILE)
    a = ap.parse_args()
    syms = [s.strip().upper() for s in a.symbols.split(",") if s.strip()]
    kid, sec = load_keys(a.envfile)
    os.makedirs(OUTDIR, exist_ok=True)
    os.makedirs(os.path.dirname(CHECK), exist_ok=True)

    manifest = {"schema": "alpaca-equities-import/1",
                "fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "source": "Alpaca Market Data API v2 (data.alpaca.markets), the SAME "
                          "endpoint the alpaca MCP reads; daily bars are Alpaca's own "
                          "aggregation of the SIP tape -- not independent downloads, cite "
                          "this manifest in any campaign built on them",
                "feed": "sip", "adjustment": "all", "timeframe": a.tf,
                "start": a.start, "end": a.end or "now",
                "note_timestamps": "1Day bar t = 00:00 ET of the trading day "
                                   "(04:00Z in DST, 05:00Z otherwise), stored as-is",
                "note_last_bar": "if fetched during regular hours the LAST daily bar is "
                                 "intraday and will be revised by a re-fetch",
                "credentials": "from the alpaca MCP env file; never stored here",
                "symbols": {}}

    for sym in syms:
        bars = fetch_symbol(kid, sec, sym, a.tf, a.start, a.end or None)
        if len(bars) < 100:
            raise SystemExit(f"{sym}: only {len(bars)} bars -- refusing to write")
        path = os.path.join(OUTDIR, f"{sym}_{TF_ALIAS.get(a.tf, a.tf.lower())}.csv")
        rows = write_csv(path, bars)
        manifest["symbols"][sym] = {
            "file": os.path.relpath(path, ROOT).replace("\\", "/"),
            "sha256": sha256_file(path), "bars": len(rows),
            "first": dt.datetime.fromtimestamp(rows[0][0] / 1000, dt.timezone.utc)
                        .isoformat(timespec="seconds"),
            "last": dt.datetime.fromtimestamp(rows[-1][0] / 1000, dt.timezone.utc)
                       .isoformat(timespec="seconds"),
        }
        print(f"{sym}: {len(rows)} bars -> {os.path.relpath(path, ROOT)}")

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    print(f"manifest -> {os.path.relpath(MANIFEST, ROOT)}")

    # ---------------- data quality audit (persisted) -----------------------
    CHK.append("Alpaca equities import datacheck "
               + dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
    CHK.append(f"feed=sip adjustment=all tf={a.tf} window={a.start}..{a.end or 'now'}")
    import csv as _csv
    for sym in syms:
        path = os.path.join(OUTDIR, f"{sym}_{TF_ALIAS.get(a.tf, a.tf.lower())}.csv")
        ts, o, c, v = [], [], [], []
        with open(path) as f:
            rd = _csv.reader(f)
            next(rd)
            for row in rd:
                if len(row) < 6:
                    continue
                ts.append(int(row[0]))
                o.append(float(row[1])); c.append(float(row[4])); v.append(float(row[5]))
        n = len(ts)
        dups = n - len(set(ts))
        chk(f"{sym}: no duplicate timestamps", dups == 0, f"{n} bars")
        rets = [abs(c[i] / c[i - 1] - 1.0) for i in range(1, n)]
        mx = max(rets)
        chk(f"{sym}: no split-scale jump (max |1d move| < 35%)", mx < 0.35,
            f"max {mx * 100:.1f}% on {dt.datetime.fromtimestamp(ts[rets.index(mx) + 1] / 1000, dt.timezone.utc).date()}")
        gaps = [(dt.datetime.fromtimestamp(ts[i - 1] / 1000, dt.timezone.utc).date(),
                 dt.datetime.fromtimestamp(ts[i] / 1000, dt.timezone.utc).date())
                for i in range(1, n) if (ts[i] - ts[i - 1]) > 4 * 86400000]
        chk(f"{sym}: no gap over 4 calendar days (market holidays ok)", not gaps,
            "; ".join(f"{a2}->{b2}" for a2, b2 in gaps))
        medv = sorted(v)[n // 2]
        chk(f"{sym}: volume is CONSOLIDATED (median > 1M sh/day)", medv > 1e6,
            f"median {medv:,.0f}")
        for sd, factor in KNOWN_SPLITS.get(sym, []):
            i = next((j for j, t in enumerate(ts)
                      if dt.datetime.fromtimestamp(t / 1000, dt.timezone.utc).date()
                      == dt.date.fromisoformat(sd)), None)
            if i and i > 0:
                r = c[i] / c[i - 1] - 1.0
                chk(f"{sym}: split {sd} x{factor:g} shows no jump under adjustment=all",
                    abs(r) < 0.12, f"split-day return {r * 100:+.2f}%")
        rng = f"{manifest['symbols'][sym]['first'][:10]}..{manifest['symbols'][sym]['last'][:10]}"
        CHK.append(f"      {sym}: {n} bars {rng}")
    # harness compatibility: the binance-style reader must parse these files
    sys.path.insert(0, HERE)
    import vrun as V
    desc = V._read_input(os.path.join(OUTDIR, f"{syms[0]}_{TF_ALIAS.get(a.tf, a.tf.lower())}.csv"))
    chk("harness _read_input parses the csv (open_ts, ms epoch)", True,
        f"{desc['bars']} bars {desc['start'][:10]}..{desc['end'][:10]} sha {desc['sha256'][:12]}")

    CHK.append("")
    CHK.append("ALL PASS")
    with open(CHECK, "w", encoding="utf-8") as f:
        f.write("\n".join(CHK) + "\n")
    print(f"\nALL PASS - datacheck written to {os.path.relpath(CHECK, ROOT)}")


if __name__ == "__main__":
    main()
