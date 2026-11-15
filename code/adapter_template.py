#!/usr/bin/env python
"""adapter_template.py -- COPY ME, then fill the marked slots. Not an adapter.

CHECKLIST for a new strategy idea (the whole pipeline, ~30 minutes):

  1. PORT. Copy this file to code/<name>_engine.py. Write the signal in
     `build_signal` and the execution rules in `execute` (or replace both).
     Keep the ported constants EXACTLY as the source declares them -- nothing
     tuned, nothing invented. Declare every convention in the docstring:
     fill bar, tie-breaking (stop first), gap rule, sizing, costs, window,
     warmup, end-of-data behavior.
  2. AUDIT FIRST. Fill KNOWN_ANSWERS with hand-computed cases on synthetic
     bars (entry/exit, stop-out, gap-through, tie, warmup) and run
     `python code/<name>_engine.py` -- ALL PASS is required BEFORE any
     real-data run. Expectation bugs count against the test, not the engine:
     re-check data ranges, epoch units, closed-vs-open trades (the audited
     lesson: 3/3 audit failures were the test's fault).
  3. REGISTER. Add to ADAPTERS in code/vrun.py (see the snippet at the bottom
     of this file): sources, version, inputs, run. The harness then gives the
     strategy hashing, run_id, verify, stale, guard for free.
  4. RUN. `python code/vrun.py run --strategy <name> --tf 1h --symbol SYM`.
     Generation-2 data cuts make the artifact immune to later appends.
  5. GATES. Screen with `bt.py` (results/bt_plans/), then WF (3 geometries),
     neighborhood, stats -- the pipeline runs each stage only for survivors.
  6. VERDICT. Every number cites its run_id; `vrun.py guard --report --strict`
     must pass; the verdict goes into STATUS.md. Per AGENTS.md REGLA 1 the
     verdict is built ONLY from this strategy's own artifacts — the kill list
     is history, never a pre-gate, and another strategy's failure (however
     similar) is never evidence about this one. bt.py `one` runs exactly that
     isolated battery.

ENGINE CONTRACT (what vrun expects):  run_symbol(paths, params) ->
    metrics: {"return_pct", "profit_factor", "n_trades", "win_rate",
              "max_dd_pct", ... plus any gate metric you want bt.py to read}
    prov:    {"adapter": <name>, "engine_version": "<name>-1"}
    tables:  [list of row dicts; give rows an "id" key so bt.py gates and
              _matrix_cols can read them]

COSTS: repo standard 5 bps fee + 0.5 bps slip per side (11 bps round trip).
The zero-cost control below runs INSIDE the artifact (drag_pp is measured,
never derived -- guard cannot back a reader's subtraction).

This template self-tests on synthetic bars only: python code/adapter_template.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ENGINE_VERSION = "template-1"
COSTS = {"repo": dict(fee=0.0005, slip=0.00005),   # 5 + 0.5 bps per side
         "zero": dict(fee=0.0, slip=0.0)}
INIT = 10_000.0


# ════════════════════════════════════════ signal (FILL THIS IN) ═══════════
def build_signal(df: pd.DataFrame, params: dict) -> dict:
    """Return aligned arrays on the CLOSED bar: enter_long / enter_short /
    exit_long / exit_short (bool), stop_dist (float, signal-bar distance,
    frozen at the signal), optional target_dist / max_bars.

    Conventions already handled by the executor below (do not re-implement):
    signal on bar i close -> fill at bar i+1 open; stop wins ties; an open
    that gaps through the stop fills AT THE OPEN; funding is NOT modelled
    here (perp engines must charge it at real settlement instants -- see
    cbpack_funding_engine.py for the pattern and its parity audit).
    """
    n = len(df)
    c = df["close"].values
    # ── FILL: your signal logic ──────────────────────────────────────
    enter_long = np.zeros(n, bool)
    enter_short = np.zeros(n, bool)
    exit_long = np.zeros(n, bool)
    exit_short = np.zeros(n, bool)
    stop_dist = np.full(n, np.nan)
    # example placeholder: long when close rises over the prior 20-bar high
    hi20 = pd.Series(df["high"]).rolling(20).max().shift(1).values
    enter_long[:] = (c > hi20) & ~np.isnan(hi20)
    stop_dist[:] = np.where(enter_long, c * 0.02, np.nan)
    return dict(enter_long=enter_long, enter_short=enter_short,
                exit_long=exit_long, exit_short=exit_short,
                stop_dist=stop_dist)


# ════════════════════════════════════════ executor (audited once, reused) ═
def execute(df: pd.DataFrame, sig: dict, fee: float, slip: float) -> dict:
    """Next-open fills, stop-first on ties, gap-through fills at the open,
    1% risk sizing to the frozen stop distance, end-of-data force close."""
    o, h, l, c = (df[k].values for k in ("open", "high", "low", "close"))
    n = len(df)
    long_e = np.asarray(sig["enter_long"], bool)
    long_x = np.asarray(sig.get("exit_long", np.zeros(n, bool)), bool)
    stop_d = np.asarray(sig["stop_dist"], float)
    risk = 0.01

    eq = np.ones(n)
    cash, qty, entry, stop = INIT, 0.0, 0.0, 0.0
    entry_i = -1
    trades = []
    for i in range(1, n):
        px = o[i]
        if qty > 0:
            exit_px, why = None, ""
            if long_x[i - 1]:
                exit_px, why = px, "exit_signal"
            elif l[i] <= stop:
                exit_px, why = min(px, stop), "stop"   # gap-through -> open
            if exit_px is not None:
                fill = exit_px * (1 - slip)
                cash += qty * fill * (1 - fee)
                trades.append(dict(entry_i=entry_i, exit_i=i, why=why,
                                   pnl=(fill - entry) * qty))
                qty = 0.0
        if qty == 0 and long_e[i - 1] and np.isfinite(stop_d[i - 1]) and stop_d[i - 1] > 0:
            stop = stop_d[i - 1]
            fill = px * (1 + slip)
            qty = (cash * risk / stop) / fill
            qty = min(qty, cash * (1 - fee) / fill)      # no leverage
            entry = fill
            entry_i = i
            cash -= qty * fill * (1 + fee)
            stop = entry - stop
        eq[i] = cash + qty * c[i]
    if qty > 0:                                        # end of data: force close
        fill = c[-1] * (1 - slip)
        cash += qty * fill * (1 - fee)
        trades.append(dict(entry_i=entry_i, exit_i=n - 1, why="end_of_data",
                           pnl=(fill - entry) * qty))
        qty = 0.0
        eq[-1] = cash
    return dict(eq=eq, trades=trades)


# ════════════════════════════════════════ adapter entry point ═════════════
def run_symbol(paths, params: dict):
    """Harness contract: (metrics, prov, tables). Zero-cost control measured
    in-artifact. Slice params (sim_start/sim_end) are declared, not assumed."""
    p = dict(params)
    df = pd.concat([pd.read_csv(x) for x in paths], ignore_index=True)
    df.columns = [str(x).strip().lower() for x in df.columns]
    df["open_ts"] = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
    df = df.drop_duplicates("open_ts").sort_values("open_ts").reset_index(drop=True)
    sig = build_signal(df, p)

    rows, m = [], {}
    for cost_name, cc in COSTS.items():
        out = execute(df, sig, cc["fee"], cc["slip"])
        eq, trades = out["eq"], out["trades"]
        pnls = np.array([t["pnl"] for t in trades], float)
        gp = pnls[pnls > 0].sum()
        gl = -pnls[pnls < 0].sum()
        ret = float(eq[-1] / INIT - 1)
        peak = np.maximum.accumulate(eq)
        mdd = float((eq / peak - 1).min())
        rows.append(dict(id=f"{cost_name}", kind="cost", cost=cost_name,
                         net_pct=100 * ret, pf=(gp / gl if gl else np.inf),
                         n=len(trades), maxDD_pct=100 * mdd))
        if cost_name == "repo":
            m.update(return_pct=100 * ret, profit_factor=(gp / gl if gl else np.inf),
                     n_trades=len(trades), max_dd_pct=100 * mdd)
        if cost_name == "zero":
            m["ret_zero_pct"] = 100 * ret
            m["drag_pp"] = m.get("ret_zero_pct", 0.0) - m.get("return_pct", 0.0)
    m["cost_bp_roundtrip"] = 11.0
    prov = {"adapter": "template", "engine_version": ENGINE_VERSION}
    return m, prov, rows


# ════════════════════════════════════════ known answers (FILL THIS IN) ════
# Hand-computed expectations on synthetic bars. A failure here is the TEST's
# fault three times out of three until proven otherwise -- check ranges, units
# and closed-vs-open trades before touching the engine.
def _known_answers() -> list:
    t0 = 1_600_000_000_000
    bars = lambda *rows: pd.DataFrame(
        rows, columns=["open_ts", "open", "high", "low", "close", "volume"])
    cases = []
    # ── FILL: one case per execution rule ──────────────────────────────
    # example: flat market -> no trades, flat equity
    df = bars(*[(t0 + i * 3_600_000, 100.0, 101.0, 99.0, 100.0, 1.0)
                for i in range(40)])
    out = execute(df, dict(enter_long=np.zeros(40, bool), stop_dist=np.full(40, np.nan)),
                  **{k: v for k, v in COSTS["repo"].items()})
    cases.append(("no signal -> flat", out, dict(n_trades=0, final_eq=INIT)))
    return cases


def _selftest() -> int:
    fails = 0
    for name, out, expect in _known_answers():
        got_n = len(out["trades"])
        got_eq = float(out["eq"][-1])
        ok = got_n == expect["n_trades"] and abs(got_eq - expect["final_eq"]) < 1e-9
        print(f"{'PASS' if ok else 'FAIL'} {name}: n={got_n} eq={got_eq:.4f}")
        fails += not ok
    print(f"\n{len(_known_answers())} known answers, {fails} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())


# ════════════════════════════════════════ registration snippet ════════════
# Paste into ADAPTERS in code/vrun.py (and import nothing there -- vrun loads
# this module by path):
#
#     "template": {
#         "sources": [os.path.join(CODE, "<name>_engine.py")],
#         "version": "<name>-1",
#         "inputs": lambda tf, sym: [
#             os.path.join(TF_DIR[tf][0], f"{sym}_{TF_DIR[tf][1]}.csv")],
#         "run": run_<name>, "matrix": True, "needs_tf": True,
#     },
#
# with in vrun.py:
#
#     def run_<name>(paths, params):
#         import importlib
#         m = _load_module(os.path.join(CODE, "<name>_engine.py"), "<name>_engine")
#         out = m.run_symbol(paths, dict(params))
#         return out["metrics"], out["prov"], out["tables"]
#
# Then: python code/vrun.py run --strategy <name> --tf 1h --symbol BTCUSDT
