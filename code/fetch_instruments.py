#!/usr/bin/env python3
"""
fetch_instruments.py — snapshot of Binance instrument metadata (public, no keys).

Fetches the CURRENT exchangeInfo from Binance spot and USDT-M futures and
writes NEW files only:

  data/instruments/spot_exchangeInfo.json   raw spot response
  data/instruments/fapi_exchangeInfo.json   raw fapi response
  data/INSTRUMENTS_MANIFEST.json            schema, fetched_utc, sha256, counts

LIMITATION (stated in the manifest too): Binance does not publish HISTORICAL
point-in-time instrument rules, so this is a current-snapshot only. Rules that
changed over a backtest window (tick/lot/minNotional/leverage brackets) and
delistings cannot be reconstructed from public data; any use of this snapshot
inside a long backtest is an approximation and must be declared as such.

Usage:
  python code/fetch_instruments.py
  python code/instruments_check.py --symbol XRPUSDT --market fapi --price 2.5 --qty 25
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "instruments"

SOURCES = [
    ("spot", "https://api.binance.com/api/v3/exchangeInfo"),
    ("fapi", "https://fapi.binance.com/fapi/v1/exchangeInfo"),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "instruments-manifest/1",
        "built_by": "code/fetch_instruments.py",
        "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": {},
        "limitations": [
            "current snapshot only: Binance publishes no historical point-in-time "
            "instrument rules, so tick/lot/minNotional/leverage changes over a "
            "backtest window are NOT reconstructable from public data",
            "no delisting history: survivorship bias is possible in any universe "
            "built from today's listed symbols",
            "consumer: code/instruments_check.py validates a price/qty against "
            "these rules; the XRP live bot asserts the same rules live per cycle",
        ],
    }
    for name, url in SOURCES:
        print(f"fetching {name} exchangeInfo ...")
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        path = OUT / f"{name}_exchangeInfo.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        n = len(data.get("symbols", []))
        manifest["sources"][name] = {
            "url": url,
            "file": str(path.relative_to(REPO)).replace("\\", "/"),
            "sha256": sha256_file(path),
            "n_symbols": n,
            "server_time_utc": datetime.fromtimestamp(
                data.get("serverTime", 0) / 1000, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ") if data.get("serverTime") else None,
        }
        print(f"  -> {path.name}: {n} symbols")

    mpath = REPO / "data" / "INSTRUMENTS_MANIFEST.json"
    mpath.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"manifest written: {mpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
