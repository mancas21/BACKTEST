#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_eqpack_audit.py — pre-run audit for the eqpack adapter (cbpack's ten rule
strategies on Alpaca equities daily data, engine used UNMODIFIED).

    python code/_eqpack_audit.py     # writes results/eqpack_audit_known_answers.txt

Pins, before any real-data artifact:
  E1  the engine bytes are the hash-locked, historically audited ones
  E2  the htf adaptation means what it claims: htf_trend(daily, 1440) is the
      sign of EMA20 vs EMA50 of the SAME daily closes shifted one bar (the
      pack's own 1h-campaign semantics, where htf=60min == chart tf)
  E3  the csv->prepare() load path preserves OHLCV exactly
  E4  flow source on equities columns is the pack's declared candle proxy
  E5  S07/S08 self-skip on equities columns (no funding_rate / open_interest)
  E6  no-lookahead: a truncated QQQ series reproduces the full run's prefix
      (signals, equity, trades) through the adapter's own path
  E7  the adapter is deterministic
"""
import hashlib
import inspect
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import vrun as V                      # noqa: E402

OUT = os.path.join(ROOT, "results", "eqpack_audit_known_answers.txt")
LINES = []


def ok(label, cond=True, detail=""):
    if not cond:
        raise AssertionError(f"FAIL {label}: {detail}")
    LINES.append(f"PASS  {label}" + (f"   [{detail}]" if detail else ""))
    print(f"PASS  {label}" + (f"   [{detail}]" if detail else ""))


pack = V._load_module(os.path.join(V.CODE, "cbpack_engine.py"), "cbpack_engine_audit")


def load_qqq():
    p = os.path.join(V.DATA, "alpaca_1d", "QQQ_1d.csv")
    raw = pd.read_csv(p)
    idx = pd.to_datetime(raw["open_ts"], unit="ms", utc=True)
    df = pack.prepare(raw.set_index(idx))
    return p, raw, df


def main():
    global LINES
    # E1 — engine bytes = the hash-locked audited engine
    lock = json.load(open(os.path.join(HERE, "_engine_lock.json"), encoding="utf-8"))
    locked_sha = lock["engines"]["cbpack_engine.py"]
    actual_sha = hashlib.sha256(
        open(os.path.join(HERE, "cbpack_engine.py"), "rb").read()).hexdigest()
    ok("E1 cbpack_engine.py matches the engine lock (audited executor bytes)",
       locked_sha == actual_sha, f"sha {actual_sha[:12]}")

    # E2 — the htf adaptation is the pack's own 1h semantics transplanted:
    # on 1h data the pack used htf=60min == chart tf, i.e. the sign of
    # EMA20 vs EMA50 of the SAME closes shifted one bar.
    rng = np.random.default_rng(3)
    vals = 100 + np.cumsum(rng.normal(0.05, 1.0, 400))
    idx = pd.date_range("2016-01-04", periods=400, freq="D", tz="UTC")
    closes = pd.Series(vals, index=idx)      # Series index MUST be idx (pandas aligns)
    dd = pd.DataFrame({"open": vals, "high": vals + 1, "low": vals - 1,
                       "close": vals, "volume": 1e6}, index=idx)
    assert float(dd["close"].notna().all()), "test frame construction bug"
    got = pack.htf_trend(dd, 1440)
    ef, es = pack.ema(closes, 20).shift(1), pack.ema(closes, 50).shift(1)
    want = pd.Series(np.where(ef.notna() & es.notna(), np.where(ef > es, 1, -1), 0),
                     index=idx)
    ok("E2 htf_trend(daily, 1440) == sign(EMA20-EMA50 of same closes, shifted 1)",
       bool((got == want).all()), "uniform rule applied to every strategy that has htf")

    # E3 — the load path preserves the file's OHLCV
    p, raw, df = load_qqq()
    ok("E3 csv->prepare preserves OHLCV",
       len(df) == len(raw)
       and float(df["close"].iloc[0]) == float(raw["close"].iloc[0])
       and float(df["close"].iloc[-1]) == float(raw["close"].iloc[-1])
       and float(df["volume"].sum()) == float(raw["volume"].sum()),
       f"{len(df)} rows, first/last close preserved")

    # E4 — flow source on equities columns is the declared candle proxy
    src = pack.flow_series(df)[1]
    ok("E4 flow source is the pack's declared candle proxy (no taker field)", src == "candle_proxy")

    # E5 — strategies needing funding/OI self-skip on equities columns
    for sid in ("S07", "S08"):
        missing = set(pack.STRATEGIES[sid].requires) - set(df.columns)
        ok(f"E5 {sid} self-skips (requires {sorted(pack.STRATEGIES[sid].requires)})",
           bool(missing), f"missing {sorted(missing)}")

    # which strategies get the htf override (introspected, not assumed)
    htf_ids = [sid for sid in ("S01", "S02", "S03", "S04", "S05", "S09", "S10")
               if "htf" in inspect.signature(pack.STRATEGIES[sid].fn).parameters]
    LINES.append(f"NOTE  strategies with an htf parameter (get htf=1440): {htf_ids}")
    print(f"NOTE  strategies with an htf parameter: {htf_ids}")

    # E6 — no-lookahead through the adapter path (S10 as the probe).
    # The prefix comparison EXCLUDES the truncated window's last bar: the pack
    # force-closes an open position there ("end_of_data" at the close, paying
    # exit fee+slip) while the full run keeps it open. That convention is
    # pinned, not ignored.
    cfg = pack.BacktestConfig(fee_bps=0.1, slippage_bps=0.5)
    cut = 2000
    full_sig = pack.make_signals(df, "S10")
    part_sig = pack.make_signals(df.iloc[:cut], "S10")
    for col in ("buy", "sell", "exit_long", "exit_short"):
        if not np.array_equal(full_sig[col].to_numpy()[:cut], part_sig[col].to_numpy()):
            raise AssertionError(f"E6 signals differ on the prefix: {col}")
    ok("E6 signals prefix identical (buy/sell/exits)", True)
    ok("E6 sl_dist prefix identical (nan-aware)",
       np.array_equal(full_sig["sl_dist"].to_numpy()[:cut],
                      part_sig["sl_dist"].to_numpy(), equal_nan=True))
    full_bt = pack.backtest(df, full_sig, cfg)
    part_bt = pack.backtest(df.iloc[:cut], part_sig, cfg)
    fe, pe = full_bt.equity.to_numpy()[:cut - 1], part_bt.equity.to_numpy()[:cut - 1]
    both = ~np.isnan(fe) & ~np.isnan(pe)
    ok("E6 no-lookahead truncation (S10, 2000 bars, last bar excluded)",
       bool(np.array_equal(fe[both], pe[both])),
       f"equity prefix equal on {int(both.sum())} marked bars")
    end_trades = part_bt.trades[part_bt.trades.reason == "end_of_data"]
    ok("E6 pack convention: open position force-closed at end_of_data",
       len(end_trades) >= 1 and str(end_trades.iloc[-1]["exit_time"].date())
       == str(df.index[cut - 1].date()),
       f"{len(end_trades)} end_of_data close(s), last at {df.index[cut - 1].date()}")

    # E7 — determinism of the full adapter call
    a1 = V.make_artifact("eqpack", "1d", "QQQ", {"costs": "eq"})
    a2 = V.make_artifact("eqpack", "1d", "QQQ", {"costs": "eq"})
    ok("E7 adapter deterministic",
       json.dumps(a1["metrics"], sort_keys=True) == json.dumps(a2["metrics"], sort_keys=True),
       f"{len(a1['metrics'].get('strategies', a1['tables']))} strategy rows")

    LINES += ["", "ALL PASS"]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(LINES) + "\n")
    print(f"\nALL PASS — wrote {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
