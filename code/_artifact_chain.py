#!/usr/bin/env python
"""_artifact_chain.py -- tamper-evidence for results/runs/ (audit M5).

Wraps the reference layer's hash chain (`_gates_v2.chain_append` /
`chain_verify`) over the whole artifact store. The chain is a sidecar
(results/runs/_CHAIN.jsonl); it does NOT touch the artifacts or the run_id, so
existing verification semantics are unchanged. After this file exists, any
byte change to any chained artifact is detectable by `verify` here, on top of
the harness's own bit-for-bit re-run check.

    python code/_artifact_chain.py build     # (re)build the chain from the store
    python code/_artifact_chain.py verify    # exit 0 only if the chain holds
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _gates_v2 as G

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")
CHAIN = os.path.join(RUNS, "_CHAIN.jsonl")


def build() -> int:
    files = [p for p in sorted(glob.glob(os.path.join(RUNS, "*.json")))
             if not os.path.basename(p).startswith("_")]
    if os.path.exists(CHAIN):
        os.remove(CHAIN)
    for p in files:
        G.chain_append(CHAIN, p)
    ok, bad = G.chain_verify(CHAIN, RUNS)
    print(f"chained {len(files)} artifacts; verify: {'OK' if ok else 'BROKEN'}")
    for b in bad[:5]:
        print("  ", b)
    return 0 if ok else 1


def verify() -> int:
    if not os.path.exists(CHAIN):
        print("no chain file; run build first")
        return 2
    ok, bad = G.chain_verify(CHAIN, RUNS)
    n = sum(1 for _ in open(CHAIN, encoding="utf-8"))
    print(f"chain holds {n} entries; verify: {'OK' if ok else 'BROKEN'}")
    for b in bad[:10]:
        print("  ", b)
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    raise SystemExit(build() if cmd == "build" else verify())
