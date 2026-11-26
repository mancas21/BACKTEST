"""Known-answer / parity audit for the MTF top-down port.
Before any market number: source hash, source causality, trade-level parity
with the source engine on real SOL 5m, both directions, funding sign,
accounting identity.

Run: python code/_mtf_topdown_audit.py ; exit 0 all pass, 2 any fail.
"""
import hashlib
import os
import sys

import numpy as np
import pandas as pd

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)
sys.path.insert(0, CODE)

import vrun as V  # noqa: E402
import mtf_topdown_source as S  # noqa: E402
import mtf_topdown_engine as E  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (("  | " + str(detail)) if detail else ""))


def main():
    print("\n== source integrity ==")
    orig = r"C:\Users\Lenovo\Downloads\mtf_topdown-strategy-claude.py"
    h1 = hashlib.sha256(open(orig, "rb").read()).hexdigest()
    h2 = hashlib.sha256(open(os.path.join(CODE, "mtf_topdown_source.py"), "rb").read()).hexdigest()
    check("copied source is byte-identical to the attachment", h1 == h2, h1)
    check("the declared hash in the engine matches the source",
          h2 == "833aedf770bad9c3f7b0b7860d5cbe9d2a2a2c790319b1b175a4f62f16a2d945",
          h2)

    print("\n== real SOLUSDT 5m: source causality and parity ==")
    path = os.path.join(ROOT, "data", "binance_klines_5m", "SOLUSDT_5m.csv")
    df5 = S.load_csv(path)
    cfg = S.Cfg()
    f = S.build_features(df5, cfg)
    check("source features are causal (its own test_causality passes)",
          bool(S.test_causality(df5, cfg)))
    src = S.backtest(f, cfg)
    ours, funded, resid = E.execute(f, cfg, cfg.fee, cfg.slip, {})
    cols = ["entry_time", "exit_time", "side", "entry", "exit", "qty", "pnl"]
    same = len(src) == len(ours) and (
        len(src) == 0 or np.allclose(src[cols].to_numpy(float),
                                     ours[cols].to_numpy(float), rtol=0, atol=1e-9))
    check("harness executor reproduces the source trades on identical signals",
          same, f"source {len(src)} trades, harness {len(ours)} trades")
    check("no funding charged in the parity run",
          funded == 0.0 and abs(resid) < 1e-6, f"funded {funded}, resid {resid:.2e}")

    print("\n== both directions, costs and funding ==")
    sides = set(ours["side"].to_numpy(int)) if len(ours) else set()
    check("both long and short trades exist in the parity book",
          sides == {1, -1} or (len(sides) > 0 and cfg.allow_short is False),
          f"sides {sorted(sides)}")
    expensive, _, _ = E.execute(f, cfg, 0.0005, 0.00005, {})
    check("repo costs reduce net equity vs author costs on the same signals",
          expensive.pnl.sum() < ours.pnl.sum(),
          f"{ours.pnl.sum():.2f} -> {expensive.pnl.sum():.2f}")
    rates = {int(df5.index[i].timestamp() * 1000): 0.001
             for i in range(0, len(df5), 100)}
    with_f, paid, resid2 = E.execute(f, cfg, cfg.fee, cfg.slip, rates)
    check("funding is real cash and the identity still closes",
          paid != 0.0 and abs(resid2) < max(1e-6, 1e-8 * abs(E.INIT + with_f.pnl.sum())),
          f"paid {paid:.4f}, resid {resid2:.2e}")

    print("\n== real artifact ==")
    a = V.make_artifact("mtftopdown", "5m", "SOLUSDT", {"costs": "repo"}, cut_ts=None)
    m = a["metrics"]
    check("artifact identity closes and declares the source hash",
          abs(m["pnl_identity_resid"]) < 1e-4 and
          a["provenance"]["source_sha256"] == h2,
          f"resid {m['pnl_identity_resid']}, trades {m['n_trades']}")

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", FAIL)
        sys.exit(2)
    print("ALL PASS")


if __name__ == "__main__":
    main()
