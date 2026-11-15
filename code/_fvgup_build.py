"""_fvgup_build.py — generates code/fvg_upgrades_portfix.py from the
byte-identical attachment code/fvg_upgrades.py with ONE declared port patch.

THE DEFECT (pandas-3.0 unit mismatch, measured on this repo's environment,
pandas 3.0.5): FineData.__init__ computes the 1m lookup window as

    step = pd.Timedelta(cfg.ltf_rule).to_timedelta64().astype("int64")

and pairs it with `P.idx.values.astype("int64")`. On pandas 2.x both are
nanoseconds; on pandas 3.0 the DatetimeIndex values are MICROseconds while
the Timedelta integer stays NANOseconds, so the window is 1000x too wide:
measured cnt ~= 15,000 one-minute bars per 15m parent (10.4 days), the OHLC
integrity check fails on every bar, pct_usable = 0.0008% (1 bar of 131,424)
and the "1m-resolved" book silently runs coarse — 131,423 coarse bars, 1 fine.

THE FIX (one literal patch, unit-agnostic): derive the window from the 1m
tape's own spacing times the expected bar count — identical semantics on any
pandas unit:

    step = int(self.ts[1] - self.ts[0])
           * int(pd.Timedelta(cfg.ltf_rule) / pd.Timedelta("1min"))

The builder REFUSES unless the source file matches the recorded attachment
sha (sidecar code/_fvgup_build_sha.json, pinned on first build) and the patch
matches exactly once. The original attachment is NEVER modified.

History: a first generated variant patched EventEngineV2._strategy to reset
the state machine on zone invalidation (vector semantics); it did NOT resolve
the measured parity divergence (27 vs 28 trades unchanged) and was REVERTED —
the re-arm-semantics reconciliation belongs to the pack's author. This
builder carries only the pandas-3.0 port fix.
"""

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "fvg_upgrades.py")
OUT = os.path.join(HERE, "fvg_upgrades_portfix.py")
SIDECAR = os.path.join(HERE, "_fvgup_build_sha.json")

OLD = '        step = pd.Timedelta(cfg.ltf_rule).to_timedelta64().astype("int64")'
NEW = ('        step = int(self.ts[1] - self.ts[0])'  # FVGUP-PORTFIX (pandas 3.0 units)
       ' * int(pd.Timedelta(cfg.ltf_rule) / pd.Timedelta("1min"))')


def main():
    if not os.path.exists(SRC):
        sys.exit(f"REFUSED: source of record {SRC} is missing")
    sha = hashlib.sha256(open(SRC, "rb").read()).hexdigest()
    if os.path.exists(SIDECAR):
        rec = json.load(open(SIDECAR, encoding="utf-8"))
        if rec.get("source_sha256") != sha:
            sys.exit(f"REFUSED: fvg_upgrades.py changed since the pin "
                     f"({rec.get('source_sha256')[:16]} -> {sha[:16]}). "
                     f"Re-verify the attachment before rebuilding.")
    else:
        json.dump({"source_sha256": sha,
                   "pinned_utc": "2026-11-13",
                   "patch": "FineData step: derive the 1m lookup window from "
                            "the tape's own spacing (pandas-3.0 unit fix; the "
                            "original mixes us datetime ints with a ns "
                            "Timedelta int -> 1000x window, fine silently "
                            "dead)"},
                  open(SIDECAR, "w", encoding="utf-8"), indent=1)
        print(f"[build] pinned attachment sha {sha[:16]}")
    src = open(SRC, encoding="utf-8", newline="").read()
    n = src.count(OLD)
    if n != 1:
        sys.exit(f"REFUSED: patch matches {n} times (must be exactly once)")
    open(OUT, "w", encoding="utf-8", newline="").write(src.replace(OLD, NEW))
    out_sha = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    print(f"[build] wrote {OUT} (sha {out_sha[:16]}) from {sha[:16]}, 1 patch")


if __name__ == "__main__":
    main()
