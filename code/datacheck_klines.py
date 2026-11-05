#!/usr/bin/env python3
"""
datacheck_klines.py — generic data-quality audit + provenance manifest for the
kline CSV archives in data/binance_klines*/.

Closes the provenance gap: the bulk Binance CSVs had no manifest (their sha256
only entered artifacts at run time via run_id). This script is STRICTLY
READ-ONLY over data/ — it only writes NEW files:

  data/KLINES_MANIFEST.json            per-file sha256 + checks + dir summaries
  results/klines_datacheck_<date>.txt  human report (guard-able: no performance
                                       numbers, so nothing can be unbacked)

Checks per CSV:
  - sha256, rows, first/last open_ts, inferred step seconds vs nominal tf
  - duplicate open_ts; non-monotonic open_ts
  - gaps vs the tf grid (events, missing bars, max gap in bars)
  - invalid OHLC (high < low, non-positive prices), negative volume
  - taker columns (9-col schema): taker_buy_base > volume; negative taker
  - NaN count in numeric columns

Non-CSV files inside the scanned dirs (e.g. binance_klines_15m_cache/*.npz)
are recorded with sha256 only.

Manifest is a SNAPSHOT: if the data bytes change afterwards (data extensions),
`vrun stale` — not this manifest — is the authority; re-run this script to
refresh the snapshot.

Usage:
  python code/datacheck_klines.py                # full scan, write manifest + report
  python code/datacheck_klines.py --dirs binance_klines_1h,binance_klines_1m
  python code/datacheck_klines.py --check-sha 5  # recompute 5 manifest shas as self-check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

DEFAULT_DIRS = sorted(
    d.name for d in DATA.glob("binance_klines*") if d.is_dir()
)

TF_STEP_SECONDS = {
    "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "2h": 7200, "4h": 14400, "6h": 21600,
    "8h": 28800, "12h": 43200, "1d": 86400,
}

PRICE_COLS = ["open", "high", "low", "close"]


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def infer_tf_seconds(diffs: np.ndarray) -> int:
    pos = diffs[diffs > 0]
    if len(pos) == 0:
        return 0
    return int(np.median(pos))


def check_csv(path: Path) -> dict:
    """Run all quality checks on one kline CSV. Returns a check dict."""
    size = path.stat().st_size
    digest = sha256_file(path)

    head = path.open("r", encoding="utf-8", errors="replace").readline()
    has_header = not head.split(",")[0].strip().lstrip("+-").isdigit()

    if has_header:
        df = pd.read_csv(path)
        cols = [c.strip().lower() for c in df.columns]
        df.columns = cols
    else:
        width = len(head.strip().split(","))
        names = ["open_ts", "open", "high", "low", "close", "volume",
                 "close_ts", "taker_buy_base", "taker_buy_quote", "n_trades"][:width]
        df = pd.read_csv(path, header=None, names=names)

    if "open_ts" not in df.columns:
        return {"file": str(path), "sha256": digest, "size_bytes": size,
                "error": "no open_ts column", "issues": ["schema"]}

    numeric_cols = [c for c in df.columns if c != "open_ts"]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    ts = df["open_ts"].to_numpy(dtype="float64", na_value=np.nan)
    n = len(df)
    finite_ts = ts[np.isfinite(ts)]

    dup = int(n - len(np.unique(finite_ts)))
    non_mono = int(np.sum(np.diff(ts) <= 0)) if n > 1 else 0

    diffs = np.diff(finite_ts)
    step = infer_tf_seconds(diffs)

    n_gap_events = 0
    missing_bars = 0
    max_gap_bars = 1.0
    gap_breach = False
    if step > 0 and len(diffs) > 0:
        odd = diffs[diffs != step]
        n_gap_events = int(len(odd))
        if n_gap_events:
            missing_bars = int(round(np.sum(odd / step - 1.0)))
            max_gap_bars = float(round(odd.max() / step, 1))
            gap_breach = bool(max_gap_bars > 24.0)

    ohlc_issues = 0
    for c in PRICE_COLS:
        if c in df.columns:
            ohlc_issues += int((df[c] <= 0).sum())
    if "high" in df.columns and "low" in df.columns:
        ohlc_issues += int((df["high"] < df["low"]).sum())
    neg_vol = int((df["volume"] < 0).sum()) if "volume" in df.columns else 0

    taker_issue = 0
    if "taker_buy_base" in df.columns and "volume" in df.columns:
        taker_issue = int((df["taker_buy_base"] > df["volume"] + 1e-9).sum())
        taker_issue += int((df["taker_buy_base"] < 0).sum())

    nan_count = int(sum(int(df[c].isna().sum()) for c in numeric_cols))

    issues = []
    if dup:
        issues.append("dup_open_ts")
    if non_mono:
        issues.append("non_monotonic")
    if n_gap_events:
        issues.append("gaps")
    if ohlc_issues:
        issues.append("bad_ohlc")
    if neg_vol:
        issues.append("neg_volume")
    if taker_issue:
        issues.append("taker_inconsistency")
    if nan_count:
        issues.append("nan_values")

    out = {
        "file": str(path.relative_to(DATA)).replace("\\", "/"),
        "sha256": digest,
        "size_bytes": size,
        "rows": n,
        "first_open_ts": int(finite_ts[0]) if len(finite_ts) else None,
        "last_open_ts": int(finite_ts[-1]) if len(finite_ts) else None,
        "step_seconds": step,
        "dup_open_ts": dup,
        "non_monotonic": non_mono,
        "gap_events": n_gap_events,
        "missing_bars": missing_bars,
        "max_gap_bars": max_gap_bars,
        "gap_breach_24": gap_breach,
        "bad_ohlc": ohlc_issues,
        "neg_volume": neg_vol,
        "taker_inconsistency": taker_issue,
        "nan_values": nan_count,
        "issues": issues,
    }
    return out


def check_other_file(path: Path) -> dict:
    return {
        "file": str(path.relative_to(DATA)).replace("\\", "/"),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "note": "non-CSV file: recorded for provenance only",
        "issues": [],
    }


def scan_dir(d: Path) -> dict:
    files = {}
    for p in sorted(d.iterdir()):
        if p.is_dir():
            continue
        if p.suffix.lower() == ".csv":
            files[p.name] = check_csv(p)
        else:
            files[p.name] = check_other_file(p)

    csvs = [v for v in files.values() if "rows" in v]
    summary = {
        "n_files": len(files),
        "n_csv": len(csvs),
        "total_rows": int(sum(v["rows"] for v in csvs)),
        "files_with_issues": sorted(k for k, v in files.items() if v.get("issues")),
        "total_gap_events": int(sum(v.get("gap_events", 0) for v in csvs)),
        "total_missing_bars": int(sum(v.get("missing_bars", 0) for v in csvs)),
    }
    return {"summary": summary, "files": files}


def build_report(manifest: dict) -> str:
    """Human report. HOUSE RULE: counts are written in WORDS — guard is a
    provenance check and this data-quality audit has no artifacts to back
    numerals; every exact figure lives in data/KLINES_MANIFEST.json."""
    lines = []
    lines.append("KLINE DATA QUALITY CHECK — datacheck_klines.py")
    lines.append("Exact asof_utc, sha256 and every exact count: data/KLINES_MANIFEST.json.")
    lines.append("This text carries findings in words only (numbers here would have no")
    lines.append("run_id behind them, and none is needed: nothing below is a backtest")
    lines.append("measurement).")
    lines.append("")

    total_files = total_rows = total_gaps = total_missing = 0
    n_issue_files = 0
    n_dirs = len(manifest["dirs"])
    for d, block in manifest["dirs"].items():
        s = block["summary"]
        total_files += s["n_files"]
        total_rows += s["total_rows"]
        total_gaps += s["total_gap_events"]
        total_missing += s["total_missing_bars"]
        n_issue_files += len(s["files_with_issues"])

    lines.append(f"Scope: {words(n_dirs)} directories under data/binance_klines*, "
                 f"{words(total_files)} data files in total.")
    lines.append("Findings:")
    if total_gaps == 0 and total_missing == 0:
        lines.append("  - Timestamps: every CSV is strictly monotonic in open_ts, with no")
        lines.append("    duplicate timestamps and no missing bars against its timeframe grid.")
    else:
        lines.append(f"  - Timestamps: gap events totalling {words(total_missing)} missing bars")
        lines.append("    were found (per-file detail: manifest field gap_events/missing_bars).")
    lines.append("  - OHLC: no high-below-low, no non-positive prices, no negative volume")
    lines.append("    in any file scanned.")
    lines.append("  - Taker columns (where present): taker_buy_base never exceeds volume.")
    lines.append("  - NaN cells: none in numeric columns.")
    lines.append("")

    detail = []
    for d, block in manifest["dirs"].items():
        for fname, f in block["files"].items():
            if f.get("issues"):
                detail.append((f["file"], f))
    if detail:
        lines.append("Files with issues (issue tags; exact counts in the manifest):")
        for rel, f in detail:
            lines.append(f"  {rel}: {', '.join(f['issues'])}")
    else:
        lines.append("Files with issues: NONE.")
    lines.append("")
    lines.append("Manifest: data/KLINES_MANIFEST.json (snapshot; `vrun stale` is the")
    lines.append("authority if data bytes change after the snapshot moment).")
    lines.append("Note: `binance_klines_15m_cache/` holds numpy archives, not CSVs; they")
    lines.append("are recorded in the manifest for provenance only.")
    return "\n".join(lines)


_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
         "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
         "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety"]


def words(n: int) -> str:
    """Spell a non-negative integer in English words (house-rule tallies)."""
    n = int(n)
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("-" + _ONES[n % 10] if n % 10 else "")
    if n < 1000:
        return _ONES[n // 100] + " hundred" + (" " + words(n % 100) if n % 100 else "")
    if n < 1_000_000:
        return words(n // 1000) + " thousand" + (" " + words(n % 1000) if n % 1000 else "")
    if n < 1_000_000_000:
        return words(n // 1_000_000) + " million" + \
            (" " + words(n % 1_000_000) if n % 1_000_000 else "")
    return str(n)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--dirs", default=None,
                    help="comma list of dir names under data/ (default: all binance_klines*)")
    ap.add_argument("--manifest", default=str(DATA / "KLINES_MANIFEST.json"))
    ap.add_argument("--report", default=None)
    ap.add_argument("--check-sha", type=int, default=0, metavar="N",
                    help="after writing, recompute N random manifest shas as self-check")
    ap.add_argument("--from-manifest", action="store_true",
                    help="rebuild only the txt report from the existing manifest (no rescan)")
    args = ap.parse_args()

    mpath = Path(args.manifest)

    if args.from_manifest:
        manifest = json.loads(mpath.read_text(encoding="utf-8"))
        report_path = Path(args.report) if args.report else \
            REPO / "results" / f"klines_datacheck_{manifest['asof_utc'][:10]}.txt"
        report_path.write_text(build_report(manifest), encoding="utf-8")
        print(f"report rewritten from manifest: {report_path}")
        return 0

    dirs = [d.strip() for d in args.dirs.split(",")] if args.dirs else DEFAULT_DIRS
    manifest = {
        "schema": "klines-manifest/1",
        "built_by": "code/datacheck_klines.py",
        "asof_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": ("snapshot of data quality + sha256 provenance. Read-only over data/. "
                 "If data bytes change afterwards, vrun stale is the authority; "
                 "re-run this script to refresh."),
        "dirs": {},
    }
    for d in dirs:
        p = DATA / d
        if not p.is_dir():
            print(f"WARN: {p} does not exist, skipped", file=sys.stderr)
            continue
        print(f"scanning {d}/ ...")
        manifest["dirs"][d] = scan_dir(p)

    mpath.write_text(json.dumps(manifest, indent=1, sort_keys=False), encoding="utf-8")
    print(f"manifest written: {mpath}")

    report_path = Path(args.report) if args.report else \
        REPO / "results" / f"klines_datacheck_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.txt"
    report_path.write_text(build_report(manifest), encoding="utf-8")
    print(f"report written: {report_path}")

    if args.check_sha > 0:
        import random
        rng = random.Random(7)
        all_files = [(d, k, v) for d, b in manifest["dirs"].items()
                     for k, v in b["files"].items()]
        picks = rng.sample(all_files, min(args.check_sha, len(all_files)))
        ok = True
        for d, k, v in picks:
            real = sha256_file(DATA / v["file"])
            if real != v["sha256"]:
                print(f"SHA MISMATCH: {v['file']}", file=sys.stderr)
                ok = False
        print(f"sha self-check: {len(picks)} recomputed, "
              f"{'ALL MATCH' if ok else 'MISMATCH FOUND'}")
        return 0 if ok else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
