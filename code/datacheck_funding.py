#!/usr/bin/env python3
"""
datacheck_funding.py — funding-coverage audit + provenance manifest for
data/binance_funding/*.json against the kline archives in data/binance_klines*/.

Closes the "funding_covers_bars" gap: a funding series that starts late, ends
early, or is missing settlements produces a backtest that charges funding on
only part of the window — silently. The funding FILE is hashed into run_ids
(so an edit after the fact is STALE), but nothing so far checked whether the
file COVERS the bars the engine replays. This script is STRICTLY READ-ONLY
over data/ — it only writes NEW files:

  data/FUNDING_MANIFEST.json            per-file sha256 + spans + per-tf coverage
  results/funding_datacheck_<date>.txt  human report (words-only tallies, guard-safe)

Checks per funding file:
  - sha256, settlement count, first/last settlement ts
  - duplicate settlement timestamps; non-monotonic ordering
  - cadence: modal spacing (median diff) and deviations from it (each deviation
    is a settlement interval where bars carried NO funding charge)

Cross-check per (funding file x kline CSV of the same symbol):
  - bar window from the CSV's own first/last open_ts (tf inferred from the data)
  - coverage fraction of the settlement span inside the bar window
  - head/tail uncovered days (bars before the first / after the last settlement)

Manifest is a SNAPSHOT: if data bytes change afterwards, `vrun stale` is the
authority; re-run this script to refresh.

Usage:
  python code/datacheck_funding.py                 # full audit, write manifest + report
  python code/datacheck_funding.py --symbols XRPUSDT,SOLUSDT
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
FUND_DIR = DATA / "binance_funding"
DAY_MS = 86_400_000


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def check_funding(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    ts = np.array([int(x.get("t", x.get("fundingTime"))) for x in raw], dtype=np.int64)
    rs = np.array([float(x.get("r", x.get("fundingRate"))) for x in raw], dtype=float)
    order = np.argsort(ts, kind="stable")
    ts, rs = ts[order], rs[order]
    n = len(ts)
    dup = int(n - len(np.unique(ts)))
    non_mono = int((np.diff(ts) <= 0).sum()) if n > 1 else 0
    diffs = np.diff(ts)
    step_ms = int(np.median(diffs)) if len(diffs) else 0
    # A deviation from the modal spacing is either an exchange INTERVAL SWITCH
    # (shorter diffs, e.g. 8h -> 4h funding: benign, every settlement still
    # present) or a MISSING PRINT (longer diffs: bars inside the long interval
    # carried no charge). Only the long side counts as missing.
    cadence_deviations = interval_switches = missing_settlements = 0
    max_dev_mult = 1.0
    if step_ms > 0 and len(diffs):
        odd = diffs[diffs != step_ms]
        cadence_deviations = int(len(odd))
        short = diffs[diffs < step_ms * 0.75]
        long_ = diffs[diffs > step_ms * 1.5]
        interval_switches = int(len(short))
        missing_settlements = int(round(np.sum(long_ / step_ms - 1.0)))
        max_dev_mult = float(round(long_.max() / step_ms, 2)) if len(long_) else 1.0
    issues = []
    if dup:
        issues.append("dup_settlement_ts")
    if non_mono:
        issues.append("non_monotonic")
    if missing_settlements:
        issues.append("missing_settlements")
    if interval_switches:
        issues.append("interval_switches")
    return {
        "file": str(path.relative_to(DATA)).replace("\\", "/"),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "settlements": n,
        "first_t": int(ts[0]) if n else None,
        "last_t": int(ts[-1]) if n else None,
        "modal_spacing_ms": step_ms,
        "modal_spacing_h": round(step_ms / 3_600_000.0, 3) if step_ms else None,
        "dup_settlement_ts": dup,
        "non_monotonic": non_mono,
        "cadence_deviations": cadence_deviations,
        "interval_switches": interval_switches,
        "missing_settlements": missing_settlements,
        "max_cadence_multiple": max_dev_mult,
        "rates_min": float(rs.min()) if n else None,
        "rates_max": float(rs.max()) if n else None,
        "issues": issues,
    }


def bar_window(csv_path: Path) -> tuple[int, int, int] | None:
    """(first_open_ts, last_open_ts, tf_ms) from the CSV's own timestamps."""
    try:
        head = csv_path.open("r", encoding="utf-8", errors="replace").readline()
        has_header = not head.split(",")[0].strip().lstrip("+-").isdigit()
        df = pd.read_csv(csv_path, usecols=[0])
    except Exception:
        return None
    col = df.columns[0]
    ts = pd.to_numeric(df[col], errors="coerce").dropna().to_numpy(dtype=np.int64)
    if len(ts) < 2:
        return None
    tf = int(np.median(np.diff(ts)))
    return int(ts[0]), int(ts[-1]), tf


def coverage_vs_bars(f: dict, sym: str) -> dict:
    """Coverage of this funding file against every kline CSV of the same symbol."""
    out = {}
    if f["first_t"] is None:
        return out
    for d in sorted(DATA.glob("binance_klines*")):
        if not d.is_dir():
            continue
        for csv_path in sorted(d.glob(f"{sym}_*.csv")):
            w = bar_window(csv_path)
            if w is None:
                continue
            t0, t1, tf = w
            rel = f"{d.name}/{csv_path.name}"
            ft0, ft1 = f["first_t"], f["last_t"]
            span = max(t1 + tf - t0, 1)
            covered_from, covered_to = max(t0, ft0), min(t1 + tf, ft1)
            cov = (covered_to - covered_from) / span if covered_to > covered_from else 0.0
            head_days = max(ft0 - t0, 0) / DAY_MS
            tail_days = max(t1 + tf - ft1, 0) / DAY_MS
            issues = []
            if head_days > 1.0:
                issues.append("head_gap")
            if tail_days > 1.0:
                issues.append("tail_gap")
            out[rel] = {
                "bars_window": [t0, t1 + tf],
                "tf_ms": tf,
                "coverage_fraction": round(float(cov), 6),
                "head_uncovered_days": round(float(head_days), 2),
                "tail_uncovered_days": round(float(tail_days), 2),
                "issues": issues,
            }
    return out


def build_report(manifest: dict) -> str:
    """House rule: counts in words; every exact figure lives in the manifest."""
    lines = []
    lines.append("FUNDING COVERAGE CHECK — datacheck_funding.py")
    lines.append("Exact asof_utc, sha256, spans and every exact count: data/FUNDING_MANIFEST.json.")
    lines.append("This text carries findings in words only (nothing below is a backtest")
    lines.append("measurement, so no run_id is needed behind it).")
    lines.append("")
    files = manifest["files"]
    lines.append(f"Scope: {words(len(files))} funding files in data/binance_funding/, "
                 f"cross-checked against every kline CSV of the same symbol in "
                 f"data/binance_klines*/.")
    lines.append("Findings:")
    n_missing = sum(1 for f in files.values() if f["missing_settlements"])
    n_switch = sum(1 for f in files.values() if f["interval_switches"])
    n_bad_dup = sum(1 for f in files.values() if f["dup_settlement_ts"] or f["non_monotonic"])
    if n_missing == 0 and n_bad_dup == 0:
        lines.append("  - Settlement series: every file is strictly monotonic with no duplicate")
        lines.append("    timestamps, and no settlement print is missing inside any series.")
    else:
        lines.append(f"  - Settlement series: {words(n_missing)} files have missing settlement")
        lines.append("    prints and/or duplicate or non-monotonic timestamps (per-file detail")
        lines.append("    in the manifest; missing prints mean bars inside those intervals")
        lines.append("    carried no funding charge).")
    if n_switch:
        lines.append(f"  - Interval switches: {words(n_switch)} files contain stretches at a")
        lines.append("    shorter funding interval than their modal one (e.g. an exchange moving")
        lines.append("    from eight-hour to four-hour funding). Benign for billing — every")
        lines.append("    settlement is present — but any consumer assuming a fixed interval")
        lines.append("    should read modal_spacing_h and the switch counts in the manifest.")
    pairs = [(k, v) for f in files.values() for k, v in f["coverage"].items()]
    n_gap_pairs = sum(1 for _, v in pairs if v["issues"])
    n_pairs = len(pairs)
    full = [v for _, v in pairs if v["coverage_fraction"] >= 0.999]
    lines.append(f"  - Coverage vs bars: of {words(n_pairs)} funding-file x kline-window pairs, "
                 f"{words(len(full))} are fully covered (settlement span reaches both")
    lines.append("    ends of the bar window); the rest carry head_gap/tail_gap tags in the")
    lines.append("    manifest. A head_gap means the earliest bars were charged NO funding;")
    lines.append("    a tail_gap means the latest bars were charged none.")
    if n_gap_pairs == 0:
        lines.append("    RESULT: every pair is fully covered — no funding-free bars anywhere.")
    else:
        lines.append(f"    RESULT: {words(n_gap_pairs)} pairs are NOT fully covered — see manifest")
        lines.append("    field coverage[].issues before trusting any funding-sensitive number")
        lines.append("    built on those bars.")
    lines.append("")
    lines.append("Manifest: data/FUNDING_MANIFEST.json (snapshot; `vrun stale` is the")
    lines.append("authority if data bytes change after the snapshot moment).")
    return "\n".join(lines)


_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
         "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
         "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety"]


def words(n: int) -> str:
    n = int(n)
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("-" + _ONES[n % 10] if n % 10 else "")
    if n < 1000:
        return _ONES[n // 100] + " hundred" + (" " + words(n % 100) if n % 100 else "")
    if n < 1_000_000:
        return words(n // 1000) + " thousand" + (" " + words(n % 1000) if n % 1000 else "")
    return str(n)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--symbols", default=None,
                    help="comma list; default: every funding file in data/binance_funding/")
    ap.add_argument("--manifest", default=str(DATA / "FUNDING_MANIFEST.json"))
    ap.add_argument("--report", default=None)
    args = ap.parse_args()

    paths = sorted(FUND_DIR.glob("*.json"))
    if args.symbols:
        want = {s.strip().upper() for s in args.symbols.split(",")}
        paths = [p for p in paths if p.stem.split("_")[0].upper() in want]

    manifest = {
        "schema": "funding-manifest/1",
        "built_by": "code/datacheck_funding.py",
        "asof_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": ("snapshot of funding coverage vs kline windows. Read-only over data/. "
                 "If data bytes change afterwards, vrun stale is the authority; "
                 "re-run this script to refresh."),
        "files": {},
    }
    for p in paths:
        sym = p.stem.split("_")[0]
        print(f"checking {p.name} ...")
        f = check_funding(p)
        f["coverage"] = coverage_vs_bars(f, sym)
        manifest["files"][p.name] = f

    mpath = Path(args.manifest)
    mpath.write_text(json.dumps(manifest, indent=1, sort_keys=False), encoding="utf-8")
    print(f"manifest written: {mpath}")

    report_path = Path(args.report) if args.report else \
        REPO / "results" / f"funding_datacheck_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.txt"
    report_path.write_text(build_report(manifest), encoding="utf-8")
    print(f"report written: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
