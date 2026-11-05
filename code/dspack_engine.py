#!/usr/bin/env python
"""dspack -- adapter runner for the DeepSeek five-strategy pack
(`deepseek_python_20261022_de5792.py`, shipped UNMODIFIED as
`code/deepseek_pack.py`; this runner IMPORTS it -- no byte edits -- and adds
what the harness contract needs).

The pack file declares NO imports, NO costs, NO execution engine and NO
numbers: it is five pure signal functions only. Everything below is
capital-D Declared:

STRATS (author call paths, verbatim defaults):
  ds1 tsmom     strat_tsmom(df)               -- log-momentum 168h, vol-target
                                               scale=clip(0.20/vol,0,2), pos=
                                               clip(sign(mom)*scale,-1,1)
  ds2 donchian  strat_donchian(df)            -- close > rolling(100).max().shift(1)
                                               (long) / < rolling(100).min().shift(1)
                                               (short), gated by expansion =
                                               (hi-lo) > 1.5 * mean(high-low,14).
                                               STATELESS: pos is rebuilt every
                                               bar from 0, so a position exists
                                               ONLY on trigger bars (exits the
                                               next bar unless it re-triggers).
  ds3 htf_ema   strat_htf_trend(df)           -- cond = close>EMA200 & EMA50>EMA200;
                                               cond -> +1, aged-out -> -1
                                               (cond .replace(0,nan)
                                               .ffill(limit=24).fillna(0)*2-1).
                                               NOTE: the output is -1, NOT flat,
                                               whenever the hold memory is gone.
  ds4 xs_mom    strat_xs_momentum(panel)      -- cross-sectional: log-mom 720h
                                               ranked pct per bar, weight 1 of
                                               (top_k=3)/(len(panel)=13),
                                               renormalized, sampled every
                                               rebalance=24 bars (iloc[::24],
                                               ffilled). Panel := the inner-join
                                               intersection of the 13 symbols.
                                               Portfolio equity factor =
                                               1 + sum_s w_s(t-1) r_s(t).
  ds5 bovol     strat_breakout_volume(df)     -- close > rolling(48).max().shift(1)
                                               and volume > 2*mean(volume,48)
                                               (long), mirrored short; ffill
                                               (limit=24) hold; flat beyond.

FILL TIME  the pack functions read data through bar t and return pos(t).
The fill happens at the CLOSE of bar t (same process_orders_on_close
convention as the audited emaadx port). So bar t+1 PnL = pos(t) *
(close[t+1]/close[t] - 1). No next-open fills, no other shift.

WEIGHT ACCOUNTING (ds1/ds2/ds3/ds5, compounding):
    L[t+1] = L[t] * (1 + pos(t-1) * r[t]) * (1 - |pos(t) - pos(t-1)| * c)
  with r[t] = close[t]/close[t-1]-1, c = taker_fee + slippage PER SIDE
  (author preset = 0.0 + 0.0: the pack file declares none; repo6x5 = 6bps+5bps).
  The fee term on |delta pos| is the turnover of EVENTS: entry |pos| when
  coming from flat, drift-fix |dpos| while holding (ds1 changes size nearly
  every bar), exit |pos| to flat, reversal |pos_new - pos_old| = whole order.

TRADE ACCOUNTING (per symbol, gate basis): a trade = a maximal run of
same-sign nonzero weight. Entry bar a = first bar of the run; the exit event
bar u = the first LATER bar whose weight is zero or opposite sign (the
position still earns bar u's return at the old weight; the exit turnover
settles at close of u). Net trade PnL_dollar = L[u+1] - L[ref] where
  ref = L[a]   if the run started from flat  -> the entry fee (at close of a)
       is INSIDE the trade's net PnL;
  ref = L[a+1] if the run started on a reversal bar (same bar as the previous
       trade's exit) -> bar a's factors already belong to the CLOSING trade,
       which carries the whole-order reversal fee (emaadx convention).
Each trade's PnL is strict: entry cost, drift fees and exit cost all inside.
Trades still open at the scored end are excluded from n/PF and reported as
n_open_at_end (their partial contribution stays in the equity).

FEE TALLY per trade: sum of fee_usd over event bars [ref_idx .. u]; the level
index ref_idx equals exactly the first bar whose fee dollars sit inside the
trade's segment. cost_share_pct = 100 * fees_charged / gross_profit_strict,
gp_strict = sum of positive net trade PnLs. A ZERO-COST control pass re-runs
the SAME pos series with c = 0 inside the artifact: ret_zero_pct, pf_zero and
drag_pp = ret_zero - ret. For the author preset drag_pp == 0 by construction
and doubles as a determinism check.

PERIOD ACCOUNTING (ds4, weight mode, MPS20 convention): a trade = a maximal
constant-weight period. Boundaries are bars where any weight changes (bar 0
always). Period i earns its holding bars and PAYS its exit switch fee at
close of the next change bar; the switch's full turnover (entry and exit
parts) is charged to the CLOSING period, except period 0 whose bar-0 entry
fee is inside its own segment (ref level = L[0]). PF/win rate read PERIOD
RETURNS; fees and concentration read period dollars. An open tail period is
excluded from n and stays in the equity. ds4 benchmark = the equal-weight
rebalanced book of the panel over the same scored span.

WINDOWS: window=full scores the whole file from bar 0. window=last6mo slices
the data to the last WARMUP_BARS+SCORE_BARS bars (2400 + 4368: the MPS20
chain's constants; the pack's largest indicator, the span-200 EMA, has seed
bias ~e^-24 after 2400 bars) and scores only the tail [WARMUP_BARS:].
ds4 needs exactly 6768 aligned bars; the 13-symbol intersection may be
shorter and the engine REFUSES the cell rather than fudging. Equity levels
carry warmup PnL, but every reported metric is a RATIO of two tail levels
(or a set of tail-only trade segments), so warmup PnL cancels
multiplicatively out of ret_pct / PF / drawdown / year returns.

BENCHMARK span: ret_pct = L[n]/L[sf] - 1 accrues bars sf..n-1 (bar 0 is a
non-earning bar under w(-1)=0 when sf=0). The symbol benchmark matches that
span exactly: close[n-1]/close[sf-1] for sf>=1, close[n-1]/close[0] for sf=0.

ANNUALIZATION: sharpe uses BARS_PER_YEAR = 8760 -- the pack's own
bars_per_year (1h). The measured median timestamp spacing is recorded as
bars_per_year_measured (8766 with a 365.25-day calendar at 3600 s spacing);
it is recorded, not used, so sharpe matches the pack's own convention.

GATES (the report tool checks; pre-declared before any real-data run):
  G1 pf_strict > 1.2   G2 n_trades >= 30  G3 pf_h1 > 1.0 and pf_h2 > 1.0
  G4 (full only) green years >= 2 of 3  G5 ret > buy&hold on the same span
  G6 conc_net_without_top5_pct > 0
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
STARTING_EQUITY = 100_000.0
BARS_PER_YEAR = 24 * 365          # the pack's own 8760 (1h bars)
WARMUP_BARS = 2400
SCORE_BARS = 4368

COST_PRESETS = {
    "author": {"taker_fee": 0.0, "slippage": 0.0},      # pack declares none
    "repo6x5": {"taker_fee": 0.0006, "slippage": 0.0005},
}

SYMBOLS13 = ["ADAUSDT", "AVAXUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "ETHUSDT",
             "HYPEUSDT", "LINKUSDT", "NEARUSDT", "SOLUSDT", "SPXUSDT", "SUIUSDT",
             "XRPUSDT"]
STRATS = ("ds1", "ds2", "ds3", "ds4", "ds5")


# ── data / author module ──────────────────────────────────────────────────
def load_author_module():
    import importlib.util
    import sys as _sys
    path = os.path.join(HERE, "deepseek_pack.py")
    if not os.path.exists(path):
        raise FileNotFoundError(
            "code/deepseek_pack.py missing -- copy the author pack into code/ "
            "before running (Downloads/ is not durable; SAX lesson)")
    spec = importlib.util.spec_from_file_location("deepseek_pack", path)
    mod = importlib.util.module_from_spec(spec)
    # The author file defines functions but imports NOTHING (np and pd are
    # never imported). Inject the namespaces the functions expect BEFORE exec:
    # the file itself stays byte-identical on disk (it is hashed into every
    # run_id through the adapter's sources list).
    mod.np = np
    mod.pd = pd
    _sys.modules["deepseek_pack"] = mod
    spec.loader.exec_module(mod)
    return mod


def _head(path: str) -> str:
    return os.path.basename(path).split("_")[0]


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    required = ["open_ts", "open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{path} missing columns {missing}")
    idx = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
    df = df.set_index(idx)[required[1:]].sort_index()
    df = df[~df.index.duplicated(keep="first")].astype(float)
    if len(df) > 2:
        spacing = int(np.median(np.diff(df.index.view("int64"))))
        if abs(spacing - 3_600_000) > 60_000:
            raise ValueError(f"{path}: median bar spacing "
                             f"{spacing / 60000:.1f} min -- dspack constants "
                             "assume 1h bars (bars_per_year=8760)")
    return df


# ── positions (author call paths, verbatim) ───────────────────────────────
def positions_single(df: pd.DataFrame, strat: str) -> np.ndarray:
    pack = load_author_module()
    if strat == "ds1":
        w = pack.strat_tsmom(df)
    elif strat == "ds2":
        w = pack.strat_donchian(df)
    elif strat == "ds3":
        w = pack.strat_htf_trend(df)
    elif strat == "ds5":
        w = pack.strat_breakout_volume(df)
    else:
        raise ValueError(f"unknown per-symbol strat {strat!r}")
    w = np.asarray(w, dtype=float)
    return np.nan_to_num(w, nan=0.0, posinf=0.0, neginf=0.0)


def positions_portfolio(df_by_sym: dict[str, pd.DataFrame],
                        lookback: int | None = None,
                        top_k: int | None = None,
                        rebalance: int | None = None) -> np.ndarray:
    """Real runs call this with NO kwargs (author verbatim defaults). The
    optional kwargs exist ONLY for the known-answer audit's small panels."""
    pack = load_author_module()
    panel = {s: df_by_sym[s] for s in sorted(df_by_sym)}
    kwargs = {}
    if lookback is not None:
        kwargs["lookback"] = int(lookback)
    if top_k is not None:
        kwargs["top_k"] = int(top_k)
    if rebalance is not None:
        kwargs["rebalance"] = int(rebalance)
    pos = pack.strat_xs_momentum(panel, **kwargs)  # dict: sym -> weight series
    cols = sorted(pos.keys())
    if cols != sorted(df_by_sym.keys()):
        raise ValueError("xs panel lost columns")
    W = pd.DataFrame({s: pos[s] for s in cols})[cols]      # deterministic order
    return np.nan_to_num(W.to_numpy(dtype=float),
                         nan=0.0, posinf=0.0, neginf=0.0)


def aligned_closes(df_by_sym: dict[str, pd.DataFrame]) -> pd.DataFrame:
    # EXACTLY the pack's own panel ops: one DataFrame per panel dict, dropna.
    return pd.DataFrame({s: d["close"] for s, d in df_by_sym.items()}).dropna()


# ── core factor chains ────────────────────────────────────────────────────
def core_factors(w: np.ndarray, close: np.ndarray, fee: float) -> dict:
    """Single symbol. w[t] is the position decided at close of bar t; equity
    accrues over bar t with w[t-1] (w[-1] := 0). Levels: lv[i] = equity after
    bar i-1 (lv[0] = starting equity)."""
    n = len(w)
    r = np.zeros(n)
    r[1:] = close[1:] / close[:-1] - 1.0
    wbase = np.zeros(n)
    wbase[1:] = w[:-1]
    grow_ret = 1.0 + wbase * r
    delta = np.empty(n)
    delta[0] = abs(w[0])                    # entry out of flat at close of bar 0
    delta[1:] = np.abs(w[1:] - w[:-1])
    fee_frac = delta * fee
    g = grow_ret * (1.0 - fee_frac)
    lv = np.empty(n + 1)
    lv[0] = STARTING_EQUITY
    lv[1:] = STARTING_EQUITY * np.cumprod(g)
    fee_usd = lv[:-1] * grow_ret * fee_frac   # fee dollars charged at close of t
    return {"lv": lv, "fee_usd": fee_usd, "n": n}


def core_factors_portfolio(W: np.ndarray, closes: np.ndarray,
                           fee: float) -> dict:
    """Multi symbol. Row t earns bar t with W[t-1] (W[-1] := 0). returns
    changes[t] = True when the weight row differs from the previous row
    (period boundaries; bar 0 too)."""
    n, k = W.shape
    r = np.zeros((n, k))
    r[1:] = closes[1:] / closes[:-1] - 1.0
    wbase = np.zeros((n, k))
    wbase[1:] = W[:-1]
    grow_ret = np.empty(n)
    grow_ret[0] = 1.0
    if n > 1:
        grow_ret[1:] = 1.0 + np.sum(wbase[1:] * r[1:], axis=1)
    delta = np.zeros(n)
    delta[0] = float(np.abs(W[0]).sum())
    if n > 1:
        delta[1:] = np.abs(W[1:] - W[:-1]).sum(axis=1)
    fee_frac = delta * fee
    g = grow_ret * (1.0 - fee_frac)
    lv = np.empty(n + 1)
    lv[0] = STARTING_EQUITY
    lv[1:] = STARTING_EQUITY * np.cumprod(g)
    fee_usd = lv[:-1] * grow_ret * fee_frac
    changes = np.zeros(n, dtype=bool)
    changes[0] = True
    if n > 1:
        changes[1:] = delta[1:] > 0.0
    return {"lv": lv, "fee_usd": fee_usd, "n": n, "changes": changes}


# ── trade segmentation (per symbol) ───────────────────────────────────────
def segment_trades(w: np.ndarray, lv: np.ndarray,
                   fee_usd: np.ndarray) -> dict:
    """Maximal same-sign runs of w. A run ends at the first LATER bar whose
    weight is 0 or the opposite sign (that bar is the exit event bar u; the
    position still earns bar u and the exit turnover settles at close of u).
    ref index convention (module docstring): flat-start ref = level a,
    reversal-start ref = level a+1 (post-fee of the previous run's exit)."""
    n = len(w)
    sgn = np.sign(w)
    trades = []
    open_run = None
    a = None            # first bar of the active run
    s_run = 0.0
    ref_kind = None     # "flat" | "rev"
    for t in range(n):
        st = sgn[t]
        if a is None:
            if st == 0.0:
                continue
            a, s_run = t, st
            ref_kind = "flat" if (t == 0 or sgn[t - 1] == 0.0) else "rev"
        elif st == s_run:
            continue    # hold (drift fees accrue at their own bars)
        else:
            u = t       # exit event bar: zero or opposite weight
            ref_idx = a if ref_kind == "flat" else a + 1
            ref_level = lv[ref_idx]
            usd = lv[u + 1] - ref_level
            trades.append({"a": int(a), "u": int(u), "side": int(s_run),
                           "ref_idx": int(ref_idx),
                           "ref_level": float(ref_level),
                           "usd": float(usd), "pnl_pct": float(usd / ref_level),
                           "fees": float(fee_usd[ref_idx:u + 1].sum())})
            a, s_run, ref_kind = None, 0.0, None
            if st != 0.0:                    # same-bar reversal -> new run
                a, s_run, ref_kind = t, st, "rev"
    if a is not None:
        ref_idx = a if ref_kind == "flat" else a + 1
        ref_level = lv[ref_idx]
        usd = lv[n] - ref_level
        open_run = {"a": int(a), "side": int(s_run), "ref_idx": int(ref_idx),
                    "ref_level": float(ref_level), "usd": float(usd),
                    "pnl_pct": float(usd / ref_level),
                    "fees": float(fee_usd[ref_idx:].sum())}
    return {"trades": trades, "open_run": open_run}


def segment_periods(lv: np.ndarray, fee_usd: np.ndarray,
                    changes: np.ndarray) -> dict:
    """ds4: maximal constant-weight periods. Bar 0 is a boundary. Period i's
    exit switch is the next change bar (that bar's return is still earned at
    the OLD weights; the switch's full turnover settles at its close and is
    charged to the CLOSING period; period 0's bar-0 entry fee is inside its
    own segment, ref level lv[0]). Period i >= 1's reference is the level
    RIGHT AFTER its own entry bar settles, lv[bars[i] + 1] -- its entry
    switch's fee and its entry bar's return both belong to the CLOSING
    period i-1, so they sit before that reference. Open tail period
    excluded from n."""
    n = len(changes)
    bars = np.flatnonzero(changes)
    periods = []
    open_period = None
    for i in range(len(bars)):
        ref_idx = 0 if i == 0 else int(bars[i]) + 1
        ref_level = lv[ref_idx]
        if i + 1 < len(bars):
            b_out = int(bars[i + 1])
            usd = lv[b_out + 1] - ref_level
            periods.append({"b": int(bars[i]), "u": b_out,
                            "ref_idx": int(ref_idx),
                            "ref_level": float(ref_level),
                            "usd": float(usd),
                            "pnl_pct": float(usd / ref_level),
                            "fees": float(fee_usd[ref_idx:b_out + 1].sum())})
        else:
            usd = lv[n] - ref_level
            open_period = {"b": int(bars[i]), "ref_idx": int(ref_idx),
                           "ref_level": float(ref_level), "usd": float(usd),
                           "pnl_pct": float(usd / ref_level),
                           "fees": float(fee_usd[ref_idx:].sum())}
    return {"periods": periods, "open_period": open_period}


def run_symbol_account(w: np.ndarray, close: np.ndarray, fee: float) -> dict:
    """Public core (the audit's reference surface): factors + segmentation for
    one position series, plus the closed-trade tiling assertion."""
    cf = core_factors(w, close, fee)
    seg = segment_trades(w, cf["lv"], cf["fee_usd"])
    if seg["trades"]:
        tot = sum(t["usd"] for t in seg["trades"])
        last = seg["trades"][-1]["u"] + 1
        ref = cf["lv"][last] - cf["lv"][0]
        if abs(tot - ref) > 1e-4:
            raise AssertionError(
                f"closed-trade dollars {tot!r} do not tile equity delta {ref!r}")
    return {"factors": cf, "seg": seg}


def run_portfolio_account(W: np.ndarray, closes: np.ndarray,
                          fee: float) -> dict:
    cf = core_factors_portfolio(W, closes, fee)
    seg = segment_periods(cf["lv"], cf["fee_usd"], cf["changes"])
    if seg["periods"]:
        tot = sum(p["usd"] for p in seg["periods"])
        last = seg["periods"][-1]["u"] + 1
        ref = cf["lv"][last] - cf["lv"][0]
        if abs(tot - ref) > 1e-4:
            raise AssertionError(
                f"period dollars {tot!r} do not tile equity delta {ref!r}")
    return {"factors": cf, "seg": seg}


# ── scoring ───────────────────────────────────────────────────────────────
def _pf_of(items) -> tuple:
    wins = [p for p in items if p > 0]
    losses = [p for p in items if p <= 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    n = len(items)
    if n == 0:
        return None, None, 0, gp, gl
    return (gp / gl if gl > 0 else None), (len(wins) / n), n, gp, gl


def _concentration(usds) -> tuple:
    total = sum(usds)
    if len(usds) >= 5 and total != 0:
        top5 = sorted(usds, reverse=True)[:5]
        return (100.0 * sum(top5) / total,
                100.0 * (total - sum(top5)) / STARTING_EQUITY)
    return None, None


def _year_returns(lv: np.ndarray, sf: int, years: np.ndarray):
    """Calendar-year equity buckets over the scored span. `years` holds the
    calendar year of each SCORED BAR (idx[sf:].year, length n - sf). Bucket
    y's ratio = lv[t1 + 1] / lv[t0] - 1 where t0/t1 are the bucket's first
    and last bar -- the bucket's COMPLETE return contribution (the level
    before its first bar's factors anchors it; nothing of the previous
    bucket's PnL carries in)."""
    if years.size == 0:
        return None
    out = []
    for y in sorted(set(int(v) for v in years)):
        pos = np.flatnonzero(years == y)
        if pos.size == 0:
            continue
        t0 = int(pos[0]) + sf
        t1 = int(pos[-1]) + sf
        if t1 + 1 >= len(lv) or lv[t0] == 0:
            continue
        out.append({"year": int(y),
                    "ret_pct": float(lv[t1 + 1] / lv[t0] - 1.0) * 100.0})
    return out or None


def _tail_return(lv: np.ndarray, sf: int, n: int) -> float:
    return float(lv[n] / lv[sf] - 1.0) * 100.0


def _tail_dd(lv: np.ndarray, sf: int) -> float:
    seg = lv[sf:]
    return float(((seg / np.maximum.accumulate(seg)) - 1.0).min()) * 100.0


def _tail_sharpe(lv: np.ndarray, sf: int) -> float | None:
    tail = np.diff(lv[sf:]) / lv[sf:-1]
    sd = float(tail.std(ddof=1)) if len(tail) > 2 else 0.0
    if sd <= 0:
        return None
    return float(tail.mean() / sd * np.sqrt(BARS_PER_YEAR))


def _score_trades(seg, lv, idx, sf, n, bench) -> dict:
    """Per-symbol trade-mode scoring. Trades counted iff exit bar u >= sf."""
    trs = seg["trades"]
    usds = [t["usd"] for t in trs if t["u"] >= sf]
    pf, wr, ntr, gp, gl = _pf_of(usds)
    row = {"n_trades": ntr, "pf_strict": pf,
           "win_rate_pct": None if wr is None else wr * 100.0,
           "gp_strict": gp, "gl_strict": gl}
    c1, c2 = _concentration(usds)
    row["conc_top5_share_pct"], row["conc_net_without_top5_pct"] = c1, c2
    row["fees_charged"] = float(sum(t["fees"] for t in trs if t["u"] >= sf))
    row["cost_share_pct"] = (100.0 * row["fees_charged"] / gp
                             if gp and gp > 0 else None)
    mid = sf + max(1, (n - sf) // 2)
    h1 = [t["usd"] for t in trs if t["u"] >= sf and t["u"] < mid]
    h2 = [t["usd"] for t in trs if t["u"] >= sf and t["u"] >= mid]
    pf_h1, _, n_h1, _, _ = _pf_of(h1)
    pf_h2, _, n_h2, _, _ = _pf_of(h2)
    row.update({"pf_h1": pf_h1, "n_h1": n_h1, "pf_h2": pf_h2, "n_h2": n_h2,
                "ret_h1_pct": (float(lv[mid] / lv[sf] - 1.0) * 100.0
                               if mid > sf else None),
                "ret_h2_pct": (float(lv[n] / lv[mid] - 1.0) * 100.0
                               if mid < n else None)})
    row["year_returns"] = _year_returns(lv, sf, np.asarray(idx[sf:].year))
    row["ret_pct"] = _tail_return(lv, sf, n)
    row["max_dd_pct"] = _tail_dd(lv, sf)
    row["sharpe"] = _tail_sharpe(lv, sf)
    row["beats_bh"] = bool(row["ret_pct"] > bench)
    row["n_open_at_end"] = 1 if seg["open_run"] else 0
    return row


def _score_periods(seg, lv, idx, sf, n, bench) -> dict:
    """ds4 period-mode scoring. Periods counted iff exit switch bar u >= sf."""
    prs = seg["periods"]
    in_scope = [p for p in prs if p["u"] >= sf]
    pcts = [p["pnl_pct"] for p in in_scope]
    pf, wr, ntr, _, _ = _pf_of(pcts)
    row = {"n_trades": ntr, "pf_strict": pf,
           "win_rate_pct": None if wr is None else wr * 100.0,
           "gp_strict": None, "gl_strict": None}
    usds = [p["usd"] for p in in_scope]
    c1, c2 = _concentration(usds)
    row["conc_top5_share_pct"], row["conc_net_without_top5_pct"] = c1, c2
    row["fees_charged"] = float(sum(p["fees"] for p in in_scope))
    gp_pos = sum(x for x in usds if x > 0)
    row["cost_share_pct"] = (100.0 * row["fees_charged"] / gp_pos
                             if gp_pos > 0 else None)
    mid = sf + max(1, (n - sf) // 2)
    p1 = [p["pnl_pct"] for p in in_scope if p["u"] < mid]
    p2 = [p["pnl_pct"] for p in in_scope if p["u"] >= mid]
    pf_h1, _, n_h1, _, _ = _pf_of(p1)
    pf_h2, _, n_h2, _, _ = _pf_of(p2)
    row.update({"pf_h1": pf_h1, "n_h1": n_h1, "pf_h2": pf_h2, "n_h2": n_h2,
                "ret_h1_pct": (float(lv[mid] / lv[sf] - 1.0) * 100.0
                               if mid > sf else None),
                "ret_h2_pct": (float(lv[n] / lv[mid] - 1.0) * 100.0
                               if mid < n else None)})
    row["year_returns"] = _year_returns(lv, sf, np.asarray(idx[sf:].year))
    row["ret_pct"] = _tail_return(lv, sf, n)
    row["max_dd_pct"] = _tail_dd(lv, sf)
    row["sharpe"] = _tail_sharpe(lv, sf)
    row["beats_bh"] = bool(row["ret_pct"] > bench)
    row["n_open_at_end"] = 1 if seg["open_period"] else 0
    return row


def _clean(v):
    if v is None:
        return None
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        x = float(v)
        return x if np.isfinite(x) else None
    return v


# ── run entry ─────────────────────────────────────────────────────────────
def _gates(row: dict, window: str) -> dict:
    """Pre-declared acceptance gates (repo criteria). G1 strict PF > 1.2;
    G2 n >= 30 closed units; G3 BOTH half-PFs > 1; G4 (full windows only)
    green complete-year buckets >= 2/3 of the years; G5 beats buy & hold on
    the scored span; G6 the book is not one lucky book: ret without its
    best five units still > 0 pct. G4 below a full window is None and is
    excluded from pass_all."""
    years = row.get("year_returns") or []
    greens = sum(1 for y in years if y["ret_pct"] > 0)
    g = {
        "pf_strict_gt_1p2": bool(row["pf_strict"] is not None
                                 and row["pf_strict"] > 1.2),
        "n_ge_30": bool(row["n_trades"] >= 30),
        "both_halves_pf_gt_1": bool(row["pf_h1"] is not None
                                    and row["pf_h2"] is not None
                                    and row["pf_h1"] > 1.0
                                    and row["pf_h2"] > 1.0),
        "beats_bh": bool(row["beats_bh"]),
        "conc_net_without_top5_pos": bool(
            row["conc_net_without_top5_pct"] is not None
            and row["conc_net_without_top5_pct"] > 0.0),
    }
    if window == "full":
        g["green_years_ge_2of3"] = bool(len(years) >= 1
                                        and greens * 3 >= 2 * len(years))
    else:
        g["green_years_ge_2of3"] = None           # not applicable
    row["gates"] = g
    row["gates_pass_all"] = bool(all(v for v in g.values() if v is not None))
    return g


def _spacing(idx: pd.DatetimeIndex):
    if len(idx) < 3:
        return None
    return int(np.median(np.diff(idx.view("int64"))))


def run_suite(paths: list[str], params: dict) -> dict:
    strat = params.get("strat")
    window = params.get("window", "full")
    cost_name = params.get("costs", "repo6x5")
    if strat not in STRATS:
        raise ValueError(f"unknown strat {strat!r}; expected {list(STRATS)}")
    if window not in ("full", "last6mo"):
        raise ValueError(f"unknown window {window!r}")
    if cost_name not in COST_PRESETS:
        raise ValueError(f"unknown cost preset {cost_name!r}; "
                         f"expected {sorted(COST_PRESETS)}")
    costs = COST_PRESETS[cost_name]
    c = float(costs["taker_fee"] + costs["slippage"])

    if strat == "ds4":
        heads = sorted(_head(p) for p in paths)
        if heads != sorted(SYMBOLS13):
            raise ValueError("ds4 needs the 13 canonical 1h files "
                             f"(got {heads})")
        df_by_sym = {h: load_csv(p) for h, p in
                     zip([_head(p) for p in paths], paths)}
        n_full = len(aligned_closes(df_by_sym))
        if window == "last6mo":
            need = WARMUP_BARS + SCORE_BARS
            if n_full < need:
                raise ValueError(f"ds4 intersection has {n_full} bars; "
                                 f"last6mo needs {need}")
            src = {s: df.iloc[-need:] for s, df in df_by_sym.items()}
        else:
            src = df_by_sym
        closes = aligned_closes(src)
        W = positions_portfolio(src)
        n = len(closes)
        if n != W.shape[0]:
            raise AssertionError(
                f"xs weights rows ({W.shape[0]}) != aligned closes rows ({n})")
        idx = closes.index
        sf = WARMUP_BARS if window == "last6mo" else 0
        # equal-weight rebalanced benchmark over the SAME scored span
        cl = closes.to_numpy()
        eq_ret = np.zeros(n)
        if n > 1:
            eq_ret[1:] = (cl[1:] / cl[:-1] - 1.0).mean(axis=1)
        grow_start = max(sf, 1)
        bench_ret = (float(np.prod(1.0 + eq_ret[grow_start:])) - 1.0) * 100.0
        acct = run_portfolio_account(W, cl, c)
        cf, seg = acct["factors"], acct["seg"]
        acct0 = run_portfolio_account(W, cl, 0.0)
        seg0 = acct0["seg"]
        row = _score_periods(seg, cf["lv"], idx, sf, n, bench_ret)
        zrow = _score_periods(seg0, acct0["factors"]["lv"], idx, sf, n, bench_ret)
        pair = "PORTFOLIO"
        aligned_bars_full = n_full
    else:
        if len(paths) != 1:
            raise ValueError(f"{strat} takes exactly one symbol file")
        sym = _head(paths[0])
        df = load_csv(paths[0])
        if window == "last6mo":
            need = WARMUP_BARS + SCORE_BARS
            if len(df) < need:
                raise ValueError(f"{sym} has only {len(df)} bars; "
                                 f"last6mo needs {need}")
            df = df.iloc[-need:]
        w = positions_single(df, strat)
        close = df["close"].to_numpy()
        n = len(df)
        idx = df.index
        sf = WARMUP_BARS if window == "last6mo" else 0
        bench_ret = ((float(close[-1] / close[sf - 1] - 1.0) * 100.0)
                     if sf >= 1 else
                     (float(close[-1] / close[0] - 1.0) * 100.0))
        acct = run_symbol_account(w, close, c)
        cf, seg = acct["factors"], acct["seg"]
        acct0 = run_symbol_account(w, close, 0.0)
        seg0 = acct0["seg"]
        row = _score_trades(seg, cf["lv"], idx, sf, n, bench_ret)
        zrow = _score_trades(seg0, acct0["factors"]["lv"], idx, sf, n, bench_ret)
        pair = sym
        aligned_bars_full = n

    row["ret_zero_pct"] = zrow["ret_pct"]
    row["pf_zero"] = zrow["pf_strict"]
    row["drag_pp"] = ((zrow["ret_pct"] - row["ret_pct"])
                      if row["ret_pct"] is not None else None)
    _gates(row, window)

    spacing_ns = _spacing(idx)
    if spacing_ns:
        bpy_meas = 365.25 * 24.0 * 3600.0 / (spacing_ns / 1e9)
    else:
        bpy_meas = None

    metrics = {
        "strat": strat, "window": window, "costs": cost_name,
        "pair": pair,
        "score_from": int(sf),
        "warmup_bars": int(sf) if window == "last6mo" else 0,
        "engine_slice_bars": int(n),
        "scored_bars": int(n - sf),
        "scored_start": str(idx[sf]), "scored_end": str(idx[-1]),
        "bars_per_year_measured": bpy_meas,
        "bench_ret_pct": bench_ret,
        "aligned_bars_full": int(aligned_bars_full),
    }
    return {"metrics": metrics, "tables": [{k: _clean(v) for k, v in row.items()}]}
