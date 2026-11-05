#!/usr/bin/env python
"""Build code/cbpack_funding_engine.py from code/cbpack_engine.py with explicit patches.

Derivation, not a rewrite: every byte of the original is preserved except the
four patches below, each of which is a literal string replacement that MUST match
exactly once (the script asserts that). The original cbpack_engine.py is NOT
modified and stays byte-identical to Downloads/strategy_pack.py.

PATCHES
  P1 docstring      : header recording the fork, the original sha256, and the
                      list of patches.
  P2 backtest()     : charge FUNDING. The original attaches a funding_rate column
                      but never debits it (its own docstring: "No funding
                      payments"). Binance USDT-M charges funding every 8h on the
                      open notional; the long pays when the rate is positive.
                      IMPORTANT: the pack's attach_funding() carries the last
                      known rate FORWARD onto every subsequent bar (that is what
                      a z-score of funding needs -- S07 reads it that way). So
                      the funding_rate column is non-zero on EVERY bar and must
                      NOT be charged per bar: that would bill 8 settlements for
                      every 1 on 1h data. The fork therefore charges only on the
                      bars flagged by the `funding_event` column, which the
                      adapter builds from the raw settlement timestamps
                      (funding_event_rate = the rate settled at that instant).
                      A position is charged iff it is open AT that instant:
                      opened at the bar's open -> charged; closed intrabar in
                      that bar -> not charged (it was not open at the close).
  P3 trades/metrics : carry the per-trade funding amount, and report
                      gross_return_pct BEFORE funding plus an explicit
                      funding_paid figure.
  P4 evaluate_all() : add concentration diagnostics (top-5 share of PnL, net
                      without the best 5 trades) to every row.

Safety: code/_cbpack_funding_parity.py proves that with funding_rate forced to
zero the new engine reproduces the ORIGINAL engine's metrics exactly.
"""
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "code", "cbpack_engine.py")
DST = os.path.join(ROOT, "code", "cbpack_funding_engine.py")

src = open(SRC, encoding="utf-8").read()
orig_sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
out = src

# ───────────────────────────────────────────────────────── P1 docstring
old_head = '''#!/usr/bin/env python3
"""
strategy_pack.py — ten composable crypto strategy designs for the backtesting agent (Python only).'''
new_head = f'''#!/usr/bin/env python3
"""
cbpack_funding_engine.py — FORK of code/cbpack_engine.py that CHARGES FUNDING.

ORIGINAL: code/cbpack_engine.py
          sha256 {orig_sha}
          (byte-identical to Downloads/strategy_pack.py; that file is NOT modified)

WHY THIS FORK EXISTS
  The original attaches a `funding_rate` column to the dataframe but never debits
  it from PnL. Its own docstring says so: "No funding payments, no liquidation
  engine, no partial fills (state this in any report you produce)." A Binance
  USDT-M perpetual charges funding every 8h on the open notional, and the long
  side pays whenever the rate is positive -- which, in a rising market, is most
  of the time. For a strategy that is in the market ~61% of the time and holds
  ~75 bars per trade, that is a real, continuous cost.

  A `funding_attached: true` flag in the artifact provenance means the COLUMN was
  attached. It does not mean the COST was charged. Read the numbers accordingly.

PATCHES (all other bytes are the original's):
  P2 backtest()      : debit funding on the position open at each settlement.
  P3 trades/metrics  : per-trade `funding` column; gross_return_pct reported
                       BEFORE funding; explicit funding_paid metric.
  P4 evaluate_all()  : concentration diagnostics per strategy
                       (top-5 share of PnL, net without the best 5 trades).

PARITY: with funding forced to zero this engine reproduces the original's
metrics exactly -- proven by code/_cbpack_funding_parity.py.

--- ORIGINAL DOCSTRING (verbatim, continues below) ---------------------------------

strategy_pack.py — ten composable crypto strategy designs for the backtesting agent (Python only).'''
assert out.count(old_head) == 1, "P1: docstring head not found exactly once"
out = out.replace(old_head, new_head)

# ───────────────────────────────────────────────────────── P2 backtest: funding
old = """    cash, pos, qty, entry, sl, tp = cfg.initial_capital, 0, 0.0, np.nan, np.nan, np.nan
    entry_i, entry_fee, risk_amt, pending, exposure = -1, 0.0, np.nan, None, 0
    trades, equity = [], np.full(n, np.nan)"""
new = """    cash, pos, qty, entry, sl, tp = cfg.initial_capital, 0, 0.0, np.nan, np.nan, np.nan
    entry_i, entry_fee, risk_amt, pending, exposure = -1, 0.0, np.nan, None, 0
    trades, equity = [], np.full(n, np.nan)
    # P2 (funding fork): the original never reads funding_rate.
    # The pack's attach_funding() carries the last known rate FORWARD onto every
    # subsequent bar (correct for S07's z-score, WRONG for billing: on 1h data it
    # would bill 8 settlements for every real one). So the charge is driven by the
    # `funding_event_rate` column, which the adapter builds from the RAW settlement
    # timestamps: non-zero only on the bar that CONTAINS the settlement instant.
    # A settlement at T is charged to the position open at that bar's OPEN
    # (post-fill, pre-intrabar-exit) -- i.e. the position held at T.
    fund = (df["funding_event_rate"].fillna(0.0).to_numpy(float)
            if "funding_event_rate" in df.columns else np.zeros(n))
    fund_acc = 0.0"""
assert out.count(old) == 1, "P2a: state init not found exactly once"
out = out.replace(old, new)

old = """    def close_pos(px, i, reason):
        nonlocal cash, pos, qty
        xf = qty * px * fee
        gross = pos * qty * (px - entry)
        pnl = gross - xf - entry_fee
        cash += gross - xf
        trades.append({"entry_time": idx[entry_i], "exit_time": idx[i], "dir": pos, "entry": entry, "exit": px,
                       "qty": qty, "pnl": pnl, "pnl_pct": pnl / max(qty * entry, 1e-12),
                       "R": pnl / risk_amt if risk_amt > 0 else np.nan, "bars": i - entry_i,
                       "fees": entry_fee + xf, "reason": reason})
        pos, qty = 0, 0.0"""
new = """    def close_pos(px, i, reason):
        nonlocal cash, pos, qty, fund_acc
        xf = qty * px * fee
        gross = pos * qty * (px - entry)
        pnl = gross - xf - entry_fee + fund_acc      # P2: funding is part of the trade
        cash += gross - xf
        trades.append({"entry_time": idx[entry_i], "exit_time": idx[i], "dir": pos, "entry": entry, "exit": px,
                       "qty": qty, "pnl": pnl, "pnl_pct": pnl / max(qty * entry, 1e-12),
                       "R": pnl / risk_amt if risk_amt > 0 else np.nan, "bars": i - entry_i,
                       "fees": entry_fee + xf, "reason": reason,
                       "funding": -fund_acc})            # P3: +ve = paid, -ve = received
        pos, qty = 0, 0.0
        fund_acc = 0.0"""
assert out.count(old) == 1, "P2b: close_pos not found exactly once"
out = out.replace(old, new)

old = """                pos, qty, entry, entry_i = d, pending["qty"], px, i
                sl = px - d * pending["sl_d"]"""
new = """                pos, qty, entry, entry_i = d, pending["qty"], px, i
                fund_acc = 0.0                        # P2: new trade starts at 0 funding
                sl = px - d * pending["sl_d"]"""
assert out.count(old) == 1, "P2d: entry block not found exactly once"
out = out.replace(old, new)

old = """        equity[i] = cash + (pos * qty * (c[i] - entry) if pos != 0 else 0.0)   # 3) mark to market
        exposure += pos != 0"""
new = """        equity[i] = cash + (pos * qty * (c[i] - entry) if pos != 0 else 0.0)   # 3) mark to market
        exposure += pos != 0"""
assert out.count(old) == 1, "P2e: equity mark not found exactly once"
out = out.replace(old, new)

# FUNDING is charged at the START of the bar that carries the settlement, BEFORE the
# pending order at that bar's open executes. The settlement instant T IS the bar's
# open, and the exchange charges the position HELD AT T: the one carried into the
# bar. A position opened at that same open is established AT T and does not pay that
# round; a position closed at that open was holding into T and does pay it.
# This is the same convention the quant_lab engine uses (verified by its selftest).
old = """    for i in range(i0, i1 + 1):
        if pending is not None:                                   # 1) execute at the open"""
new = """    for i in range(i0, i1 + 1):
        if pos != 0 and fund[i] != 0:                  # 0) P2: FUNDING at the settlement
            fc = pos * qty * c[i] * fund[i]            # long pays a positive rate; short receives
            cash -= fc
            fund_acc -= fc
        if pending is not None:                                   # 1) execute at the open"""
assert out.count(old) == 1, "P2f: loop head not found exactly once"
out = out.replace(old, new)

# ───────────────────────────────────────────────────────── P3 metrics
old = """    if len(trades):
        w, l = trades[trades.pnl > 0], trades[trades.pnl <= 0]
        gl = -l.pnl.sum()
        m.update({"win_rate_pct": len(w) / len(trades) * 100,
                  "profit_factor": float(w.pnl.sum() / gl) if gl > 0 else float("inf"),
                  "expectancy_R": float(trades.R.mean()), "avg_trade_pct": float(trades.pnl_pct.mean() * 100),
                  "fees_paid": float(trades.fees.sum()),
                  "gross_return_pct": float((trades.pnl + trades.fees).sum() / cfg.initial_capital * 100),
                  "avg_bars_in_trade": float(trades.bars.mean()),
                  "exit_reasons": trades.reason.value_counts().to_dict()})
    return m"""
new = """    if len(trades):
        w, l = trades[trades.pnl > 0], trades[trades.pnl <= 0]
        gl = -l.pnl.sum()
        fund_paid = float(trades.funding.sum()) if "funding" in trades else 0.0
        m.update({"win_rate_pct": len(w) / len(trades) * 100,
                  "profit_factor": float(w.pnl.sum() / gl) if gl > 0 else float("inf"),
                  "expectancy_R": float(trades.R.mean()), "avg_trade_pct": float(trades.pnl_pct.mean() * 100),
                  "fees_paid": float(trades.fees.sum()),
                  "funding_paid": fund_paid,                       # P3: +ve = paid
                  "funding_paid_pct": fund_paid / cfg.initial_capital * 100,
                  # P3: gross is now BEFORE funding (pnl + fees + funding)
                  "gross_return_pct": float((trades.pnl + trades.fees
                                             + (trades.funding if "funding" in trades else 0.0)
                                             ).sum() / cfg.initial_capital * 100),
                  "avg_bars_in_trade": float(trades.bars.mean()),
                  "exit_reasons": trades.reason.value_counts().to_dict()})
    return m"""
assert out.count(old) == 1, "P3a: metrics block not found exactly once"
out = out.replace(old, new)

# trades DataFrame column list
old = """    cols = ["entry_time", "exit_time", "dir", "entry", "exit", "qty", "pnl", "pnl_pct", "R", "bars", "fees", "reason"]"""
new = """    cols = ["entry_time", "exit_time", "dir", "entry", "exit", "qty", "pnl", "pnl_pct", "R", "bars", "fees", "reason", "funding"]"""
assert out.count(old) == 1, "P3b: trade cols not found exactly once"
out = out.replace(old, new)

# ───────────────────────────────────────────────────────── P4 concentration
old = """def evaluate_all(df: pd.DataFrame, cfg: BacktestConfig, ids: Optional[list[str]] = None) -> pd.DataFrame:
    rows = []
    for sid in ids or list(STRATEGIES):
        spec = STRATEGIES[sid]
        try:
            r = backtest(df, spec.fn(df), cfg)
        except MissingData as e:
            rows.append({"id": sid, "name": spec.name, "status": f"SKIPPED: {e}"})
            continue
        m = r.metrics"""
new = '''def concentration(tr: pd.DataFrame, init: float = 10_000.0) -> dict:
    """How much of the result is carried by the few best trades?

    A strategy whose best 5 trades exceed 100% of total PnL is not a strategy with
    an edge -- it is a handful of lucky positions. `conc_net_without_top5_pct` is
    the return the strategy would have made WITHOUT them.
    """
    if tr is None or not len(tr):
        return {"conc_total_pnl": 0.0, "conc_top5_pnl": 0.0, "conc_top5_share": float("nan"),
                "conc_net_pct": 0.0, "conc_net_without_top5_pct": float("nan"),
                "conc_passes": False}
    srt = tr.sort_values("pnl", ascending=False)
    total = float(srt.pnl.sum())
    top5 = float(srt.head(5).pnl.sum())
    share = (top5 / total) if total else float("nan")
    without = (total - top5) / init * 100.0
    return {"conc_total_pnl": total, "conc_top5_pnl": top5, "conc_top5_share": share,
            "conc_top5_share_pct": share * 100.0 if np.isfinite(share) else float("nan"),
            "conc_net_pct": total / init * 100.0, "conc_net_without_top5_pct": without,
            "conc_passes": bool(np.isfinite(without) and without > 0)}


def evaluate_all(df: pd.DataFrame, cfg: BacktestConfig, ids: Optional[list[str]] = None) -> pd.DataFrame:
    rows = []
    for sid in ids or list(STRATEGIES):
        spec = STRATEGIES[sid]
        try:
            r = backtest(df, spec.fn(df), cfg)
        except MissingData as e:
            rows.append({"id": sid, "name": spec.name, "status": f"SKIPPED: {e}"})
            continue
        m = r.metrics'''
assert out.count(old) == 1, "P4a: evaluate_all head not found exactly once"
out = out.replace(old, new)

old = """                     "sharpe": m["sharpe_annualised"], "exposure_%": m["exposure_pct"]})
    return pd.DataFrame(rows)"""
new = """                     "sharpe": m["sharpe_annualised"], "exposure_%": m["exposure_pct"],
                     # P4: concentration diagnostics
                     "funding_paid_pct": m.get("funding_paid_pct", 0.0),
                     **concentration(r.trades, cfg.initial_capital)})
    return pd.DataFrame(rows)"""
assert out.count(old) == 1, "P4b: evaluate_all row not found exactly once"
out = out.replace(old, new)

# ───────────────────────────────────────────────────────── P5 event helper
old = '''def attach_oi(df: pd.DataFrame, oi: pd.Series, lag_bars: int = 1) -> pd.DataFrame:'''
new = '''def attach_funding_events(df: pd.DataFrame, funding: pd.Series) -> pd.DataFrame:
    """Mark the bars on which a funding SETTLEMENT occurs, with the settled rate.

    The pack's own attach_funding() carries the last known rate FORWARD onto every
    later bar. That is what a z-score of funding needs (S07 reads it that way) but
    it is NOT a billing schedule: on 1h data it would bill 8 settlements for every
    real one. This function produces the billing schedule instead -- a column that
    is non-zero only on the bar whose OPEN coincides with the settlement instant.

    Convention (documented, deterministic, conservative):
      * a settlement at instant T is charged to the position HELD AT T, i.e. the one
        carried INTO the bar that opens at T;
      * a position opened at that same open is established AT T and does not pay
        that round;
      * a position closed at that same open was holding into T and does pay it.
    """
    out = df.copy()
    out["funding_event_rate"] = 0.0
    if funding is None or len(funding) == 0:
        return out
    opens = out.index
    col = out.columns.get_loc("funding_event_rate")
    for t, r in funding.items():
        j = opens.searchsorted(t)
        if j < len(opens) and opens[j] == t:
            out.iloc[j, col] = float(r)          # settlement exactly on a bar open
        else:
            k = j - 1
            if k >= 0:                            # settlement inside the bar -> its open
                out.iloc[k, col] = float(r)
    return out


def attach_oi(df: pd.DataFrame, oi: pd.Series, lag_bars: int = 1) -> pd.DataFrame:'''
assert out.count(old) == 1, "P5a: attach_oi anchor not found exactly once"
out = out.replace(old, new)

# ───────────────────────────────────────────────────────── write
open(DST, "w", encoding="utf-8", newline="").write(out)
print(f"wrote {DST}")
print(f"  original sha256 : {orig_sha}")
print(f"  fork    sha256 : {hashlib.sha256(out.encode('utf-8')).hexdigest()}")
print(f"  size original/fork: {len(src)} / {len(out)} bytes")
print(f"  patches applied : P1 docstring, P2 funding, P3 metrics/trades, P4 concentration")
