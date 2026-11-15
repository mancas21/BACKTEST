#!/usr/bin/env python
r"""
_p100_pairs_parity.py — parity of the repo's pair book against the pack's.

Two levels, on REAL data, for every spread prompt (81, 82, 85, 86, 88, 89):

A. SIGNAL PARITY: the arrays the port feeds to its book (side, stop, spread,
   spread open, beta) are IDENTICAL to the ones the pack's own functions
   feed to its SpreadSim. This is the signal port.

B. BOOK PARITY: with the PACK's conventions (its 0.55 bps per side, its
   linearised spread PnL, no funding), the repo's book must produce the same
   TRADES (entry bar, exit bar, side) and the same PnL as the pack's
   SpreadSim.

The repo's own conventions (11 bps, real funding) then DIFFER on purpose:
they are the declared differences, and the report attributes the gap.

Usage:  python code/_p100_pairs_parity.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
PACK = os.path.join(HERE, "prompts100")
for p in (PACK, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import p100_screen_engine as PE          # noqa: E402
import pairs_signals as PS               # noqa: E402
import backtest100_pairs_engine as PK    # noqa: E402

SPREAD_IDS = (81, 82, 85, 86, 88, 89)
PACK_FN = {81: PK.strat_81, 82: PK.strat_82, 85: PK.strat_85,
           86: PK.strat_86, 88: PK.strat_88, 89: PK.strat_89}


def pack_run(sid):
    """The pack's own run, with its SpreadSim captured."""
    captured = {"runs": []}
    orig_run = PK.SpreadSim.run

    def spy(self, side_target, stop_s, start, end):
        res = orig_run(self, side_target, stop_s, start, end)
        captured["runs"].append((start, end, res[1]))
        if "side" not in captured:
            captured["side"] = np.asarray(side_target).copy()
            captured["stop"] = np.asarray(stop_s).copy()
            captured["beta"] = np.asarray(self.beta).copy()
            captured["s"] = np.asarray(self.s).copy()
            captured["s_open"] = np.asarray(self.so).copy()
        return res

    PK.SpreadSim.run = spy
    try:
        pack_fn = PACK_FN[sid]
        pack_fn()
    finally:
        PK.SpreadSim.run = orig_run
    return captured


def main():
    results = []
    all_ok = True
    print("=== paridad de la familia de pares (81-90) ===")
    for sid in SPREAD_IDS:
        cap = pack_run(sid)
        mine = PS.pair_signal(sid)
        ok_side = np.array_equal(mine["side"], cap["side"])
        ok_stop = np.allclose(np.nan_to_num(mine["stop_s"], nan=-1e18),
                              np.nan_to_num(cap["stop"], nan=-1e18))
        ok_s = np.allclose(mine["s"], cap["s"], equal_nan=True)
        ok_so = np.allclose(mine["s_open"], cap["s_open"], equal_nan=True)
        ok_b = np.allclose(np.asarray(mine["beta"], float),
                           np.asarray(cap["beta"], float))
        sig_ok = ok_side and ok_stop and ok_s and ok_so and ok_b

        # BOOK parity with the pack's conventions, on the pack's own 70/30
        # split (IS and OOS separately, as the pack runs it)
        book_ok = True
        detail = []
        n = len(mine["s"])
        split = int(n * 0.7)
        # the pack ran two slices; they come back in order (IS, then OOS)
        for (s0, e0, pk), (label, (a0, a1)) in zip(
                cap["runs"], (("IS", (0, split - 1)), ("OOS", (split, n - 1)))):
            b = PE.SpreadBook(mine["legs"], mine, pack_conventions=True,
                              charge_funding=False)
            b.run(start_idx=a0, end_idx=a1)
            # the pack stores side as a float (+1/-1); the repo stores the
            # word. The trade itself is the same.
            def norm_side(v):
                if isinstance(v, str):
                    return "long" if v == "long" else "short"
                return "long" if float(v) > 0 else "short"

            key = lambda t: (norm_side(t["side"]), t["entry_time"],
                             t["exit_time"], round(float(t["pnl"]), 6))
            a = sorted(key(t) for t in pk)
            c = sorted(key(t) for t in b.trades)
            same = (a == c)
            book_ok &= same
            if not same:
                first = next((i for i in range(min(len(a), len(c)))
                              if a[i] != c[i]), min(len(a), len(c)))
                detail.append(f"{label}: pack {len(a)} trades vs repo "
                              f"{len(c)}; primera diferencia en {first}")

        all_ok &= sig_ok and book_ok
        results.append(dict(id=sid, signal_ok=sig_ok, book_ok=book_ok,
                             detail=detail))
        print(f"  {'OK  ' if sig_ok and book_ok else 'FALLO'} #{sid}  "
              f"señal {'=' if sig_ok else '!='}  libro {'=' if book_ok else '!='}  "
              f"({len(mine['side'])} barras)")
        for d in detail:
            print("        ", d)

    out = dict(pass_=bool(all_ok), results=results)
    p = os.path.join(HERE, "_p100_pairs_parity.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"\n{'PASS' if all_ok else 'FAIL'} -> {p}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
