#!/usr/bin/env python3
"""
fetch_aggtrades.py — download REAL historical aggTrades from the official
Binance bulk archive (data.binance.vision, futures/um daily files) for a
symbol and date range. No keys, public archive, no synthetic data.

Files land in data/aggtrades/<SYMBOL>/<SYMBOL>-aggTrades-<YYYY-MM-DD>.csv
(append-only: existing files are never re-downloaded or rewritten). A manifest
data/AGGTRADES_<SYMBOL>_IMPORT.json records source URL, sha256, rows and the
day range for every file (same provenance convention as EDGE_V41_IMPORT.json).

Futures aggTrades CSV columns (Binance archive):
  agg_trade_id, price, quantity, first_trade_id, last_trade_id,
  transact_time, is_buyer_maker

Usage:
  python code/fetch_aggtrades.py --symbol XRPUSDT --start 2026-10-11 --end 2026-10-31
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests

REPO = Path(__file__).resolve().parent.parent
BASE = "https://data.binance.vision/data/futures/um/daily/aggTrades"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def daterange(a: date, b: date):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--start", required=True, help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD (inclusive)")
    args = ap.parse_args()
    sym = args.symbol.upper()

    outdir = REPO / "data" / "aggtrades" / sym
    outdir.mkdir(parents=True, exist_ok=True)
    manifest_path = REPO / "data" / f"AGGTRADES_{sym}_IMPORT.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) \
        if manifest_path.exists() else {
            "schema": "aggtrades-import/1",
            "source": "data.binance.vision futures/um daily aggTrades (official archive)",
            "columns": ["agg_trade_id", "price", "quantity", "first_trade_id",
                        "last_trade_id", "transact_time", "is_buyer_maker"],
            "fetched_utc": None, "days": {},
        }

    s = date.fromisoformat(args.start)
    e = date.fromisoformat(args.end)
    n_new = 0
    for d in daterange(s, e):
        day = d.isoformat()
        if day in manifest["days"]:
            print(f"{day}: already in manifest, skip")
            continue
        url = f"{BASE}/{sym}/{sym}-aggTrades-{day}.zip"
        r = requests.get(url, timeout=120)
        if r.status_code == 404:
            print(f"{day}: NOT PUBLISHED YET (404) — archive lags ~1 day; aborting so "
                  f"the window stays contiguous")
            break
        r.raise_for_status()
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        name = zf.namelist()[0]
        target = outdir / f"{sym}-aggTrades-{day}.csv"
        target.write_bytes(zf.read(name))
        df = pd.read_csv(target)
        manifest["days"][day] = {
            "url": url,
            "file": str(target.relative_to(REPO)).replace("\\", "/"),
            "sha256": sha256_file(target),
            "rows": int(len(df)),
            "first_ts_ms": int(df["transact_time"].iloc[0]),
            "last_ts_ms": int(df["transact_time"].iloc[-1]),
        }
        n_new += 1
        print(f"{day}: {len(df)} trades -> {target.name}")

    manifest["fetched_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest["days_fetched"] = len(manifest["days"])
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"manifest: {manifest_path} ({manifest['days_fetched']} days total, {n_new} new)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
