"""_qwen50_preflight.py — run every qwen50 cell end-to-end on a ~60-day tail
slice of the real data (original basenames in a temp dir so _pick still
matches; funding JSONs passed whole). Catches input-resolution, build_frame,
signal-machine, metrics-schema and accounting failures before the full run
(the _s101_preflight pattern). Writes a PASS/FAIL line per id."""

import shutil
import sys
import time
import traceback
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import qwen50_engine as Q  # noqa: E402

TMP = ROOT / "data" / "_qwen50_preflight_tmp"
SLICE_ROWS = {"1m": 90_000, "5m": 20_000, "15m": 7_000, "1h": 1_800}


def slice_file(src, dst, rows):
    df = pd.read_csv(src)
    df.columns = [str(c).strip().lower() for c in df.columns]
    df.tail(rows).to_csv(dst, index=False)


def inputs_for(symbol):
    names = []
    for tf in ("1m", "5m", "15m", "1h"):
        for d in ("binance_klines_" + tf, "binance_klines_" + tf + "_taker"):
            p = ROOT / "data" / d / f"{symbol}_{tf}.csv"
            if p.exists():
                names.append(p)
                break
    f = ROOT / "data" / "binance_funding" / f"{symbol}_funding.json"
    if f.exists():
        names.append(f)
    if symbol == "ETHUSDT":
        p = ROOT / "data" / "binance_klines_5m" / "BTCUSDT_5m.csv"
        if p.exists():
            names.append(p)
    return names


def main():
    ids = sorted(set(Q.CELLS) | set(Q.NO_DATA))
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True, exist_ok=True)
    cache, sliced, paths_by_sym = {}, set(), {}
    for symbol in {Q.CELLS[i][0] for i in Q.CELLS}:
        paths = []
        for p in inputs_for(symbol):
            base = p.name
            dst = TMP / base
            if base not in sliced:
                if p.suffix == ".csv":
                    tf = base.rsplit("_", 1)[1].split(".")[0]
                    rows = SLICE_ROWS.get(tf)
                    if rows:
                        slice_file(p, dst, rows)
                    else:
                        shutil.copyfile(p, dst)
                else:
                    shutil.copyfile(p, dst)
                sliced.add(base)
            paths.append(dst)
        paths_by_sym[symbol] = [str(x) for x in paths]

    npass = nfail = nrefuse = 0
    for idn in ids:
        try:
            if idn in Q.NO_DATA:
                try:
                    Q.run([], {"id": idn})
                    print(f"[FAIL] {idn}: NO_DATA not enforced", flush=True)
                    nfail += 1
                except ValueError as e:
                    print(f"[SKIP] {idn}: {e}", flush=True)
                    nrefuse += 1
                continue
            symbol, tf_label, tf_minutes, _src = Q.CELLS[idn]
            t0 = time.time()
            m, prov, tables = Q.run(paths_by_sym[symbol], {"id": idn})
            dt = time.time() - t0
            oos = m["oos_profit_factor"]
            print(f"[PASS] {idn} {symbol} {tf_label} n={m['n_trades']} "
                  f"pf={m['profit_factor']:.2f} "
                  f"oos={oos if oos is not None else -1:.2f} "
                  f"ret={m['return_pct']:.1f}% "
                  f"cost={m['cost_bp_roundtrip']:.0f}bps {dt:.1f}s",
                  flush=True)
            npass += 1
        except Exception as e:
            print(f"[FAIL] {idn}: {type(e).__name__}: {e}", flush=True)
            traceback.print_exc(limit=3)
            nfail += 1
    print(f"\npreflight: {npass} pass, {nrefuse} refused, {nfail} fail",
          flush=True)
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
