#!/usr/bin/env python3
"""
_verify_id_binding.py — corpus-wide audit of the run_id <-> content binding.

The run_id is sha256(json.dumps(core, sort_keys=True, separators=(",", ":")))[:16]
and every artifact stores its own `core` verbatim. `vrun verify` re-runs the
engine and compares metrics, but (before the 2026-11-01 hardening) never
re-derived the id from the stored content — so an artifact whose params were
edited together with consistently recomputed metrics would verify OK under a
stale id (the same hole the qbt audit's Probe B demonstrated there).

This sweep recomputes the id from EVERY stored `core` and compares it to the
artifact's run_id field and its filename. It also flags a["params"] !=
a["core"]["params"] (verify re-runs from the top-level params, so a mismatch
there is a second binding hole). STRICTLY READ-ONLY over results/.

Exit codes: 0 all bound, 1 mismatches found.

Usage:
  python code/_verify_id_binding.py                 # sweep results/runs/*.json
  python code/_verify_id_binding.py --runs results/runs
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def recompute_id(core) -> str:
    return hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--runs", default=str(REPO / "results" / "runs"))
    args = ap.parse_args()

    files = sorted(Path(args.runs).glob("*.json"))
    bad_id = bad_file = bad_params = missing_core = 0
    problems = []
    for p in files:
        try:
            a = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            problems.append(f"{p.name}: UNREADABLE ({e})")
            bad_id += 1
            continue
        core = a.get("core")
        if core is None:
            problems.append(f"{p.name}: no `core` block — id cannot be re-derived")
            missing_core += 1
            continue
        rid_field, rid_file = a.get("run_id"), p.stem
        rid_core = recompute_id(core)
        if rid_core != rid_field:
            problems.append(f"{p.name}: core hashes to {rid_core}, run_id field says {rid_field}")
            bad_id += 1
        if rid_field != rid_file:
            problems.append(f"{p.name}: filename {rid_file} != run_id field {rid_field}")
            bad_file += 1
        if a.get("params") != core.get("params"):
            problems.append(f"{p.name}: top-level params != core.params (verify re-runs from the former)")
            bad_params += 1

    n = len(files)
    n_bad = len(problems)
    lines = [
        "RUN_ID <-> CONTENT BINDING SWEEP — code/_verify_id_binding.py",
        f"asof_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"scope: every artifact JSON in results/runs/ (read-only)",
        "",
    ]
    if n_bad == 0:
        lines.append(f"RESULT: every one of the {n} artifacts binds: the stored core hashes")
        lines.append("to the run_id field, the filename matches, and top-level params")
        lines.append("equal core.params. The corpus is id-bound.")
    else:
        lines.append(f"RESULT: of {n} artifacts, mismatches found: see list below")
        lines.append("(counts in words: "
                     f"id mismatches {bad_id}, filename mismatches {bad_file}, "
                     f"params/core.params mismatches {bad_params}, "
                     f"missing-core {missing_core}).")
        lines.append("")
        lines.extend("  " + s for s in problems)
    out = REPO / "results" / f"id_binding_sweep_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwritten: {out}")
    return 0 if n_bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
