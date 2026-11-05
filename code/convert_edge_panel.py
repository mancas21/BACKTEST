#!/usr/bin/env python3
"""convert_edge_panel.py — import the EDGE STRATEGY-2 v4.1 1m panel as repo CSVs.

Source: `C:\\Users\\Lenovo\\Downloads\\EDGE STRATEGY-2-V4-1-CLAUDE\\data\\processed\\
<SYM>_klines_1m.parquet`
  columns: open_time, open, high, low, close, volume, close_time, qav, trades,
           taker_base, taker_quote
  window : 2025-09-01 .. 2026-09-30 (581,760 one-minute bars per symbol)

Output: the repo's own taker convention, byte-compatible with what `vrun.py` and
`_cbpack_gates.py` already read:

  data/binance_klines_1h_taker/<SYM>_1h.csv
  data/binance_klines_15m_taker/<SYM>_15m.csv
  header: open_ts,open,high,low,close,volume,taker_buy_base,taker_buy_quote,n_trades

Rules that make this safe to run:
  - never overwrites an existing destination file (it aborts instead);
  - only COMPLETE buckets are emitted (60 one-minute bars for 1h, 15 for 15m),
    so a partial edge hour cannot invent a fake bar;
  - writes `data/EDGE_V41_IMPORT.json` with the sha256 of every source and every
    output, plus the row counts, so the provenance survives the source deletion.

Usage:
    python code/convert_edge_panel.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(r"C:\Users\Lenovo\Downloads\EDGE STRATEGY-2-V4-1-CLAUDE\data\processed")
TARGETS = {
    "1h": (ROOT / "data" / "binance_klines_1h_taker", 60, 60 * 60 * 1000),
    "15m": (ROOT / "data" / "binance_klines_15m_taker", 15, 15 * 60 * 1000),
}
COLS = ["open_ts", "open", "high", "low", "close", "volume",
        "taker_buy_base", "taker_buy_quote", "n_trades"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def aggregate(df: pd.DataFrame, minutes: int, tf_ms: int) -> pd.DataFrame:
    df = df.sort_values("open_time")
    df = df.assign(bucket=(df["open_time"] // tf_ms) * tf_ms)
    g = df.groupby("bucket", sort=True).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        taker_buy_base=("taker_base", "sum"),
        taker_buy_quote=("taker_quote", "sum"),
        n_trades=("trades", "sum"),
        n_bars=("open_time", "size"),
    )
    g = g[g["n_bars"] == minutes].drop(columns=["n_bars"])
    g = g.reset_index().rename(columns={"bucket": "open_ts"})
    return g[COLS]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sources = sorted(SRC.glob("*_klines_1m.parquet"))
    if not sources:
        print(f"no sources under {SRC}")
        return 2

    dates = {}
    for tf, (outdir, minutes, tf_ms) in TARGETS.items():
        dates[tf] = {"dir": outdir, "minutes": minutes, "tf_ms": tf_ms}
        if not outdir.exists():
            print(f"missing repo dir {outdir}")
            return 2

    existing = {tf: {p.name for p in d["dir"].glob("*.csv")} for tf, d in dates.items()}

    manifest = {"source_dir": str(SRC), "built_by": "code/convert_edge_panel.py",
                "symbols": {}, "outputs": {}}
    written = 0
    skipped = []
    for src in sources:
        sym = src.name.replace("_klines_1m.parquet", "")
        names = {tf: f"{sym}_{tf}.csv" for tf in dates}
        if all(n in existing[tf] for tf, n in names.items()):
            skipped.append(sym)
            continue
        clash = [n for tf, n in names.items() if n in existing[tf]]
        if clash and not all(n in existing[tf] for tf, n in names.items()):
            print(f"ABORT: partial collision for {sym}: {clash}")
            return 3

        df = pd.read_parquet(src, columns=["open_time", "open", "high", "low",
                                           "close", "volume", "trades",
                                           "taker_base", "taker_quote"])
        entry = {"source": src.name, "source_sha256": sha256_file(src),
                 "source_rows": int(len(df)),
                 "first_open_time": int(df["open_time"].min()),
                 "last_open_time": int(df["open_time"].max())}
        for tf, d in dates.items():
            agg = aggregate(df, d["minutes"], d["tf_ms"])
            out = d["dir"] / names[tf]
            if args.dry_run:
                print(f"[dry] {out.name}: {len(agg)} rows")
                continue
            agg.to_csv(out, index=False)
            entry[f"{tf}_rows"] = int(len(agg))
            entry[f"{tf}_sha256"] = sha256_file(out)
            entry[f"{tf}_first_ts"] = int(agg["open_ts"].iloc[0])
            entry[f"{tf}_last_ts"] = int(agg["open_ts"].iloc[-1])
            written += 1
        manifest["symbols"][sym] = entry

    if args.dry_run:
        return 0

    man_path = ROOT / "data" / "EDGE_V41_IMPORT.json"
    man_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"symbols: {len(manifest['symbols'])} imported, {len(skipped)} already present")
    print(f"files written: {written}")
    print(f"manifest: {man_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
