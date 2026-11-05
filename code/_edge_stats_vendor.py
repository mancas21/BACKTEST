#!/usr/bin/env python3
"""_edge_stats_vendor.py — regenerate code/edge_stats.py and prove body parity.

`code/edge_stats.py` is a VENDORED copy of `edge/engine/stats.py` with a
provenance header on top. The body below the marker line must stay
byte-identical to the source, so this script writes both the header and the
body, then re-reads the result and compares SHA-256.

Run after ANY change to edge/engine/stats.py:

    python code/_edge_stats_vendor.py           # rewrite + verify
    python code/_edge_stats_vendor.py --check   # verify only, exit 1 on drift
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "edge" / "engine" / "stats.py"
DST = ROOT / "code" / "edge_stats.py"
MARKER = "# --- BEGIN edge/engine/stats.py (byte-identical) ---\n"

HEADER = """\
# edge_stats.py -- VENDORED copy of edge/engine/stats.py (do not edit here).
#
# Source        : edge/engine/stats.py
# Source sha256 : {sha}
# Origin        : EDGE-first research project v4.1 / v6 bridge (MP section 8),
#                 migrated into this repository 2026-10-29.
# Why vendored  : `code/` is where the harness lives. Importing across the two
#                 trees would couple the backtest harness to a sealed, terminal
#                 research campaign. The copy carries this provenance header;
#                 everything below the marker line is BYTE-IDENTICAL.
# Parity        : `python code/_edge_stats_vendor.py --check` compares the body
#                 below the marker against edge/engine/stats.py.
#
# NEW to this repository (grep over code/ before the import: zero files
# contained any of them):
#   cluster_t              day-clustered CR1 t-statistic of per-trade net bps
#   benjamini_hochberg     FDR (BH) across ALL ledger screens -- the gate that
#                          pack50 and cand7 could not apply to their own trials
#   spa_test               Hansen (2005) SPA / reality check
#   mde_bps, effective_n   minimum detectable effect and the power statement
#   matched_timing_null    matched-hour timing null
#   circular_shift_null    circular-shift null for event studies
#   factor_regression      Newey-West factor regression vs BTC + basket
#
# NOT new -- already in code/quant_metrics.py; this file is not their canonical
# source, they are kept only for API parity with the original engine:
#   deflated_sharpe, pbo_cscv, sharpe_ratio, stationary_bootstrap_idx
#
# Requires numpy + scipy (both present in the repo environment).
""" + MARKER


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def build() -> bytes:
    body = SRC.read_bytes()
    return HEADER.format(sha=sha(body)).encode("utf-8") + body


def check() -> int:
    if not DST.exists():
        print(f"MISSING: {DST}")
        return 2
    want = build()
    got = DST.read_bytes()
    src_body = SRC.read_bytes()
    marker = MARKER.encode("utf-8")
    idx = got.find(marker)
    if idx < 0:
        print("FAIL: marker line not found in code/edge_stats.py")
        return 2
    body = got[idx + len(marker):]
    ok_body = sha(body) == sha(src_body)
    ok_file = sha(got) == sha(want)
    print(f"source sha256     : {sha(src_body)[:16]}")
    print(f"body byte-identical: {ok_body}")
    print(f"file up to date    : {ok_file}")
    if not ok_body:
        print("FAIL: body drifted from edge/engine/stats.py -- re-run without --check")
        return 1
    if not ok_file:
        print("note: header differs from the canonical template (body is fine)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        return check()
    DST.write_bytes(build())
    print(f"wrote {DST} ({DST.stat().st_size} bytes)")
    return check()


if __name__ == "__main__":
    sys.exit(main())
