#!/usr/bin/env python
r"""
xsml_engine.py — the `xsml` cross-sectional ML book, run with the REPO's
execution model.

Spec (frozen before the first market run): results/xsml_pre_registration.md

ENGINE VERSION 2 (2026-11-11): SIGNED-QUANTITY ACCOUNTING.
--------------------------------------------------
Version 1 of this engine multiplied a SIGNED quantity by `side` a second
time (`side * qty`), which inverted the whole short leg: the cash flow, the
mark-to-market, the trade PnL and the funding charge all had the wrong sign
for every short, and the fee was CREDITED instead of charged (the repo's
own known-answer convention is in code/scalp_wave_engine.py, where a short
SELLS at the open and BUYS BACK at the exit).

The defect was found by the repo's ACCOUNTING INVARIANT, which version 1
did not have and version 2 asserts INSIDE every artifact:

    eq[-1] - INIT == sum(pnl) - funding_paid

On the version-1 book that identity was off by 1689.65 USDT, exactly four
commissions for each of the 507 short trades. The invariant is now
asserted, and the residual is REPORTED in the artifact
(`pnl_identity_resid`), so a broken ledger fails loudly instead of
producing a plausible-looking profit factor.

CONVENTIONS (all declared; none of them is pybroker's default)
--------------------------------------------------------------
* Rebalance at the 00:00 UTC bar: the ranking uses the predictions at that
  bar's CLOSE.
* The book turns over COMPLETELY at the NEXT bar's open: every open leg is
  closed and the new book (long top-3, short bottom-3) is opened at that
  same fill. A leg that stays selected is still closed and reopened, so its
  stop is frozen at the CURRENT signal bar (the spec says the stop is
  frozen at the signal bar, not at the entry bar of an old position).
* Entry fill: next open, with slippage against the book
  (long buys at open*(1+slip), short sells at open*(1-slip)).
* Stop and target: 2 x ATR14 bps by default, measured from the fill, frozen
  at the signal bar.
* STOP FIRST on ties; a bar that opens beyond the stop fills AT THE OPEN.
* The entry bar's own range IS checked (the fill is at that bar's open, so
  its range is after the fill).
* One position per name; the book is flat between rebalances.
* Sizing: EQUAL WEIGHT — each of the six legs is 1/6 of equity (50% long,
  50% short), no leverage, gross exposure 100% of equity.
* Costs: 11 bps round trip per leg (5 bps fee + 0.5 bps slip per side),
  charged on entry and on exit, in BOTH directions.
* Funding: charged at the REAL settlements against the position held, using
  the repo's convention (a settlement at t is mapped to the first bar whose
  open is at or after t, and charged on that bar against the net position).
  A long PAYS a positive rate and a short RECEIVES it.
* The model only ever sees DEV; its predictions for OOS are read from
  data/xsml_preds*.csv, which is an INPUT of the artifact (hashed into the
  run_id).

The engine never looks at a price it is not allowed to see: predictions come
from a file, features from a file, and the price path from the store.
"""
from __future__ import annotations

import importlib.util
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

_spec = importlib.util.spec_from_file_location(
    "xsml_repo_primitives", os.path.join(HERE, "scalp_wave_engine.py"))
_repo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_repo)

ENGINE_VERSION = "xsml-2"
INIT = 10_000.0
FEE_BPS = 5.0            # per side
SLIP_BPS = 0.5           # per side
FEE = FEE_BPS / 1e4
SLIP = SLIP_BPS / 1e4
STOP_ATR_MULT = 2.0
TARGET_ATR_MULT = 2.0
TOP_K = 3
REBAL_HOUR = 0           # 00:00 UTC
MIN_NAMES = 6            # below this the date is not traded at all

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT",
           "SUIUSDT", "ARBUSDT", "JUPUSDT", "HYPEUSDT"]


# ─────────────────────────────── data loading ──────────────────────────────
def _to_ms(values):
    """Epoch MILLISECONDS from any datetime64 resolution.

    `Series.astype("int64")` returns the count in the COLUMN'S OWN UNIT, and
    pandas 3 no longer defaults to nanoseconds, so a tz-aware column can come
    back in SECONDS and silently break every as-of join against a
    millisecond series. Every timestamp here goes through this helper.
    """
    return np.asarray(values).astype("datetime64[ms]").astype("int64")


def load_symbol(sym: str):
    p = os.path.join(ROOT, "data", "binance_klines_1h", f"{sym}_1h.csv")
    df = pd.read_csv(p)
    df.columns = [c.strip().lower() for c in df.columns]
    df["ms"] = _to_ms(pd.to_datetime(df["open_ts"], unit="ms", utc=True))
    df = df.sort_values("ms").drop_duplicates("ms").reset_index(drop=True)
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    lo = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    atr = _repo.atr(h, lo, c, 14)
    with np.errstate(invalid="ignore", divide="ignore"):
        atr_bps = atr / c * 1e4
    return dict(sym=sym, ms=df["ms"].to_numpy(np.int64), open=o, high=h,
                low=lo, close=c, volume=v, atr_bps=atr_bps,
                index={int(t): i for i, t in enumerate(df["ms"])})


def funding_events(sym: str, bar_ms: np.ndarray):
    """(rate, is_event) per bar, repo convention: a settlement at t maps to
    the first bar whose OPEN is at or after t."""
    p = os.path.join(ROOT, "data", "binance_funding", f"{sym}_funding.json")
    rate = np.zeros(len(bar_ms))
    ev = np.zeros(len(bar_ms), bool)
    if not os.path.exists(p):
        return rate, ev, 0
    recs = json.load(open(p, encoding="utf-8"))
    n = 0
    for x in recs:
        t = int(x["t"])
        j = int(np.searchsorted(bar_ms, t, side="left"))
        if j < len(bar_ms):
            ev[j] = True
            rate[j] = float(x["r"])
            n += 1
    return rate, ev, n


def load_predictions(path: str):
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df["ms"] = _to_ms(pd.to_datetime(df["date"], utc=True))
    out = {}
    for sym, g in df.groupby("symbol"):
        g = g.sort_values("ms")
        out[str(sym)] = dict(ms=g["ms"].to_numpy(np.int64),
                              pred=g["pred"].to_numpy(float),
                              y=g["y"].to_numpy(float) if "y" in g else None,
                              split=g["split"].to_numpy() if "split" in g else None)
    return out


# ─────────────────────────────── the book ──────────────────────────────────
def run_book(symbols, preds, *, split="OOS", init=INIT, fee=FEE, slip=SLIP,
             top_k=TOP_K, stop_mult=STOP_ATR_MULT,
             target_mult=TARGET_ATR_MULT, charge_funding=True, track=None,
             long_only=False, short_only=False, rebalance_bars=24,
             min_names=MIN_NAMES, turnover="full"):
    """Run the cross-sectional book over one split.

    symbols : list of per-symbol dicts (from load_symbol, already filtered to
               the split, with s["pred"] aligned bar for bar)
    preds   : {sym: {ms, pred, split}} (only used for provenance)

    THE LEDGER
    ----------
    `qty` is SIGNED: positive for a long, negative for a short. It is the
    only place the direction lives, and it is used as-is everywhere:

        entry:  cash -= qty*fill + fee      (a short RECEIVES the proceeds)
        exit:   cash += qty*fill - fee      (a short BUYS BACK, paying fee)
        pnl:    qty*(exit_fill - entry_fill) - fees
        equity: cash + qty*mark             (a short is a liability)
        funding: cash -= qty*mark*rate     (a short RECEIVES a positive rate)

    Multiplying a signed quantity by `side` again is the bug this file's
    version 1 had; the known-answer suite in code/_xsml_engine_audit.py
    pins both directions down.
    """
    bars = {}
    for s in symbols:
        if "pred" not in s or len(s["pred"]) != len(s["ms"]):
            continue
        bars[s["sym"]] = dict(s)

    # funding per symbol, on ITS OWN bars (repo convention: a settlement at t
    # maps to the first bar whose open is at or after t)
    for sym, b in bars.items():
        r, e, n = funding_events(sym, b["ms"])
        b["rate"] = r
        b["is_fund"] = e

    all_ms = np.unique(np.concatenate([b["ms"] for b in bars.values()]))
    pos_of = {sym: {int(t): i for i, t in enumerate(b["ms"])}
              for sym, b in bars.items()}

    cash = init
    equity = np.full(len(all_ms), np.nan)
    open_pos = {sym: None for sym in bars}
    pending_open = []      # (sym, side, stop_bps, target_bps) -> fill at next open
    pending_close = []     # sym -> closed at the next open
    trades = []
    funding_paid = 0.0     # NET amount paid (negative = the book received)
    fees_paid = 0.0
    n_rebal = 0
    n_skipped = 0

    def sym_at(sym, t):
        b = bars.get(sym)
        if b is None:
            return None
        i = pos_of[sym].get(int(t))
        return None if i is None else (b, i)

    def close_position(sym, p, i, b, px, why):
        """Close at market price px (slippage against the book)."""
        nonlocal cash, fees_paid
        fill = px * (1 - slip * p["side"])
        f = abs(p["qty"]) * fill * fee
        cash += p["qty"] * fill - f
        fees_paid += f
        pnl = p["qty"] * (fill - p["fill"]) - p["fee_in"] - f
        trades.append(dict(symbol=sym, entry_ms=p["entry_ms"],
                           exit_ms=int(b["ms"][i]), side=p["side"], why=why,
                           pnl=pnl, entry_px=p["fill"], exit_px=fill))
        open_pos[sym] = None

    for k, t in enumerate(all_ms):
        # ── 1. fills at this bar's OPEN: closes first, then opens ──
        if pending_close:
            for sym in list(pending_close):
                p = open_pos.get(sym)
                got = sym_at(sym, t)
                if p is None or got is None:
                    continue
                b, i = got
                close_position(sym, p, i, b, b["open"][i], "rebalance")
                pending_close.remove(sym)
        if pending_open:
            for (sym, side, stop_bps, tgt_bps) in list(pending_open):
                got = sym_at(sym, t)
                if got is None:
                    continue
                b, i = got
                pending_open.remove((sym, side, stop_bps, tgt_bps))
                atr_bps = b["atr_bps"][i]
                if not np.isfinite(atr_bps) or atr_bps <= 0:
                    continue
                fill = b["open"][i] * (1 + slip * side)
                stop_dist = fill * stop_bps / 1e4
                if stop_dist <= 0:
                    continue
                notional = (init * 0.5 / top_k)      # 1/6 of equity per leg
                qty = side * notional / fill         # SIGNED quantity
                f = notional * fee
                cash -= qty * fill + f
                fees_paid += f
                open_pos[sym] = dict(side=side, qty=qty, fill=fill,
                                     entry_ms=int(t),
                                     target=fill * (1 + side * tgt_bps / 1e4),
                                     stop=fill - side * stop_dist,
                                     fee_in=f, closing=False)

        # ── 2. exits on this bar's range: STOP FIRST, gap fills at the open ──
        for sym, b in bars.items():
            p = open_pos[sym]
            if p is None or p["closing"]:
                continue
            i = pos_of[sym].get(int(t))
            if i is None:
                continue
            if p["side"] == 1:
                hit_stop = b["low"][i] <= p["stop"]
                hit_tgt = b["high"][i] >= p["target"]
            else:
                hit_stop = b["high"][i] >= p["stop"]
                hit_tgt = b["low"][i] <= p["target"]
            if hit_stop:
                px = (min(b["open"][i], p["stop"]) if p["side"] == 1
                      else max(b["open"][i], p["stop"]))
                close_position(sym, p, i, b, px, "stop")
            elif hit_tgt:
                close_position(sym, p, i, b, p["target"], "target")

        # ── 3. funding on the settlement bar, against the position held ──
        if charge_funding:
            for sym, b in bars.items():
                i = pos_of[sym].get(int(t))
                if i is None or not b["is_fund"][i] or b["rate"][i] == 0:
                    continue
                p = open_pos[sym]
                if p is None:
                    continue
                mark = b["close"][i]
                # a long PAYS a positive rate; a short RECEIVES it
                cost = p["qty"] * mark * b["rate"][i]
                cash -= cost
                funding_paid += cost

        # ── 4. equity mark-to-market ──
        eq = cash
        for sym, p in open_pos.items():
            if p is None:
                continue
            got = sym_at(sym, t)
            if got is None:
                continue
            b, i = got
            eq += p["qty"] * b["close"][i]     # a short is a liability
        equity[k] = eq

        # ── 5. rebalance: rank at this bar's CLOSE, turn the book over at the
        #       NEXT bar's open ──
        hh = (int(t) // 3_600_000) % 24
        day_num = int(t) // 86_400_000
        cadence = max(1, int(rebalance_bars) // 24)
        if hh == REBAL_HOUR and (day_num % cadence == 0) and k + 1 < len(all_ms):
            cands = []
            for sym, b in bars.items():
                i = pos_of[sym].get(int(t))
                if i is None:
                    continue
                pr = b["pred"][i]
                if not np.isfinite(pr):
                    continue
                cands.append((float(pr), sym, b["atr_bps"][i]))
            if len(cands) < min_names:
                # not enough names for a full book: this date is NOT traded
                n_skipped += 1
                continue
            cands.sort(reverse=True)
            longs = cands[:top_k]
            shorts = cands[-top_k:]
            new_set = {}
            if not short_only:
                for pr, sym, atr_bps in longs:
                    new_set[sym] = (1, stop_mult * atr_bps,
                                    target_mult * atr_bps)
            if not long_only:
                for pr, sym, atr_bps in shorts:
                    if sym in new_set:
                        continue
                    new_set[sym] = (-1, stop_mult * atr_bps,
                                    target_mult * atr_bps)
            # TURNOVER. The frozen spec (results/xsml_pre_registration.md)
            # does not say whether a leg that STAYS selected is closed and
            # reopened, and the two readings are different books with
            # first-order cost differences. Both are declared and reported
            # (results/xsml_turnover_pre_registration.md):
            #   "full" -> every open leg is closed and the new book is opened
            #             at the next open (the portfolio IS top-3/bottom-3
            #             at every rebalance, and each stop is frozen at the
            #             CURRENT signal bar)
            #   "keep" -> only the legs that LEAVE the ranking are closed; a
            #             leg that stays keeps its position, its stop and its
            #             size
            if turnover == "full":
                for sym, p in open_pos.items():
                    if p is not None and not p["closing"]:
                        p["closing"] = True
                        pending_close.append(sym)
                for sym, (side, stop_bps, tgt_bps) in new_set.items():
                    pending_open.append((sym, side, stop_bps, tgt_bps))
            elif turnover == "keep":
                for sym, p in open_pos.items():
                    if p is not None and not p["closing"] and sym not in new_set:
                        p["closing"] = True
                        pending_close.append(sym)
                for sym, (side, stop_bps, tgt_bps) in new_set.items():
                    cur = open_pos.get(sym)
                    if cur is not None and not cur["closing"]:
                        continue          # already in the book, keep it
                    pending_open.append((sym, side, stop_bps, tgt_bps))
            else:
                raise ValueError(f"unknown turnover: {turnover!r}")
            n_rebal += 1

    # ── end of data: force close ──
    for sym, p in open_pos.items():
        if p is None:
            continue
        b = bars[sym]
        i = len(b["ms"]) - 1
        close_position(sym, p, i, b, b["close"][i], "end_of_data")
    equity[-1] = cash

    out = dict(equity=equity, trades=trades, funding_paid=funding_paid,
               fees_paid=fees_paid, n_rebal=n_rebal, n_skipped=n_skipped,
               final_equity=cash, bars=len(all_ms))
    if track is not None:
        track.update(out)
    return out


# ───────────────────────────── adapter entry point ─────────────────────────
def run_symbol(paths, params):
    """Harness contract: (metrics, prov, tables)."""
    p = dict(params)
    split = str(p.pop("split", "OOS"))
    fee = float(p.pop("fee_bps", FEE_BPS)) / 1e4
    slip = float(p.pop("slip_bps", SLIP_BPS)) / 1e4
    top_k = int(p.pop("top_k", TOP_K))
    use_funding = bool(p.pop("funding", True))
    stop_mult = float(p.pop("stop_mult", STOP_ATR_MULT))
    target_mult = float(p.pop("target_mult", TARGET_ATR_MULT))
    long_only = bool(p.pop("long_only", False))
    short_only = bool(p.pop("short_only", False))
    rebalance_bars = int(p.pop("rebalance_bars", 24))
    turnover = str(p.pop("turnover", "full"))
    if p:
        raise ValueError(f"unknown xsml params: {sorted(p)}")

    symbols = []
    kline_paths = list(paths[:-1])          # the LAST path is the predictions
    for path in kline_paths:
        sym = os.path.basename(path).split("_")[0]
        symbols.append(load_symbol(sym))
    preds = load_predictions(paths[-1])

    # keep only the bars of the requested split. The predictions start at the
    # study start (2024-10), so the join is on the TIMESTAMP, not on position:
    # the klines go back years further than the features do. The prediction
    # vector is filtered with the SAME mask, so price and prediction stay
    # aligned bar for bar.
    for s in symbols:
        pr = preds.get(s["sym"], {})
        pred_full = np.full(len(s["ms"]), np.nan)
        y_full = None if pr.get("y") is None else np.full(len(s["ms"]), np.nan)
        keep = np.zeros(len(s["ms"]), bool)
        if pr.get("ms") is not None and len(pr["ms"]):
            pos = np.clip(np.searchsorted(pr["ms"], s["ms"]),
                          0, len(pr["ms"]) - 1)
            hit = pr["ms"][pos] == s["ms"]
            sp = pr.get("split")
            # `sp` is indexed by the PREDICTION rows, so the split filter is
            # mapped through `pos` (bar -> prediction row) before it is
            # combined with the bar-side mask.
            if sp is not None and len(sp) == len(pr["ms"]):
                sp_ok = (sp == split)[pos]
            else:
                sp_ok = np.ones(len(s["ms"]), bool)
            ok = hit & sp_ok
            pred_full = np.where(ok, pr["pred"][pos], np.nan)
            if y_full is not None:
                y_full = np.where(ok, pr["y"][pos], np.nan)
            keep = ok
        s["ms"] = s["ms"][keep]
        for k in ("open", "high", "low", "close", "volume", "atr_bps"):
            s[k] = s[k][keep]
        s["pred"] = pred_full[keep]
        s["index"] = {int(t): i for i, t in enumerate(s["ms"])}
        s["y"] = (y_full[keep] if y_full is not None
                  else np.full(len(s["ms"]), np.nan))

    res = run_book(symbols, preds, split=split, fee=fee, slip=slip,
                   top_k=top_k, charge_funding=use_funding,
                   stop_mult=stop_mult, target_mult=target_mult,
                   long_only=long_only, short_only=short_only,
                   rebalance_bars=rebalance_bars, turnover=turnover)
    # ZERO-COST CONTROL, inside the artifact: the same signals with no fee and
    # no slippage (funding stays, it is a real transfer, not a friction). The
    # drag is MEASURED, never derived by the reader.
    res0 = run_book(symbols, preds, split=split, fee=0.0, slip=0.0,
                    top_k=top_k, charge_funding=use_funding,
                    stop_mult=stop_mult, target_mult=target_mult,
                    long_only=long_only, short_only=short_only,
                    rebalance_bars=rebalance_bars, turnover=turnover)
    trades = res["trades"]
    pnls = np.array([t["pnl"] for t in trades], float)
    gp = float(pnls[pnls > 0].sum())
    gl = float(-pnls[pnls < 0].sum())
    pf = (gp / gl) if gl > 0 else (float("inf") if gp > 0 else 0.0)
    eq = res["equity"]
    peak = np.maximum.accumulate(eq)
    mdd = float((eq / peak - 1).min())
    net = float(eq[-1] / INIT - 1)

    # ACCOUNTING INVARIANT (the repo's rule, AGENTS.md "Porting a Pine
    # script"): the equity change must equal the sum of the net trade PnL
    # minus the funding paid, because the book ends flat. This is the check
    # that catches a fee charged on the wrong side; it runs INSIDE every
    # artifact, so a divergence fails loudly instead of producing a
    # plausible-looking profit factor.
    pnl_sum = float(pnls.sum())
    resid = (eq[-1] - INIT) - (pnl_sum - res["funding_paid"])
    if abs(resid) > max(1e-6, abs(pnl_sum) * 1e-9):
        raise AssertionError(
            f"accounting invariant broken: eq[-1]-INIT={eq[-1] - INIT:.8f} "
            f"vs sum(pnl)-funding={pnl_sum - res['funding_paid']:.8f} "
            f"(residual {resid:.8f})")

    # concentration: the best five trades as a share of total PnL
    srt = np.sort(pnls)[::-1] if len(pnls) else np.zeros(1)
    total = float(pnls.sum())
    best5 = float(srt[:5].sum())
    conc_share = (100.0 * best5 / total) if total > 0 else None
    without5 = (100.0 * (total - best5) / INIT) if len(pnls) else None

    # per-symbol PF (a book that lives on one symbol is not a book)
    per_sym = {}
    for sym in {t["symbol"] for t in trades}:
        v = np.array([t["pnl"] for t in trades if t["symbol"] == sym], float)
        g = float(v[v > 0].sum())
        l = float(-v[v < 0].sum())
        per_sym[sym] = dict(n=int(len(v)), pf=((g / l) if l > 0 else None),
                            pnl=float(v.sum()))

    # thirds of the window
    thirds = []
    e = eq[~np.isnan(eq)]
    for i in range(3):
        a = len(e) * i // 3
        b = len(e) * (i + 1) // 3
        thirds.append(100.0 * (e[b - 1] / e[a] - 1) if b > a and e[a] > 0 else 0.0)

    # forecast quality ON THE TRADED WINDOW, measured inside the artifact:
    # a book can lose while the forecast correlates, and the report must be
    # able to say so without reaching for an external file.
    pp, yy = [], []
    for s in symbols:
        if s.get("y") is None or len(s.get("y", [])) != len(s["ms"]):
            continue
        pp.append(s["pred"])
        yy.append(s["y"])
    pred_corr, n_pred = float("nan"), 0
    if pp:
        p_all = np.concatenate(pp)
        y_all = np.concatenate(yy)
        m = np.isfinite(p_all) & np.isfinite(y_all)
        n_pred = int(m.sum())
        if n_pred > 2:
            pred_corr = float(np.corrcoef(p_all[m], y_all[m])[0, 1])

    metrics = {
        "return_pct": 100 * net,
        "profit_factor": pf,
        "n_trades": int(len(trades)),
        "win_rate": 100 * float((pnls > 0).sum() / len(pnls)) if len(pnls) else 0.0,
        "max_dd_pct": 100 * mdd,
        "final_equity": float(eq[-1]),
        "init_equity": INIT,
        "cost_bp_roundtrip": 2 * (FEE_BPS + SLIP_BPS),
        "funding_paid_usdt": float(res["funding_paid"]),
        "fees_paid_usdt": float(res["fees_paid"]),
        "gross_profit_usdt": gp,
        "gross_loss_usdt": gl,
        "best5_share_pct": conc_share,
        "net_without_best5_pct": without5,
        "period1_pct": thirds[0],
        "period2_pct": thirds[1],
        "period3_pct": thirds[2],
        "n_periods_green": int(sum(1 for t in thirds if t > 0)),
        "n_rebalances": int(res["n_rebal"]),
        "n_dates_not_traded": int(res["n_skipped"]),
        "top_k": top_k,
        "funding_charged": bool(use_funding),
        "split": split,
        "stop_atr_mult": stop_mult,
        "target_atr_mult": target_mult,
        "long_only": long_only,
        "short_only": short_only,
        "rebalance_bars": rebalance_bars,
        "turnover": turnover,
        # zero-cost control (measured inside the artifact)
        "ret_zero_pct": 100 * float(res0["equity"][-1] / INIT - 1),
        "drag_pp": (100 * float(res0["equity"][-1] / INIT - 1) - 100 * net),
        "zero_cost_n_trades": int(len(res0["trades"])),
        "n_exit_stop": int(sum(1 for t in trades if t["why"] == "stop")),
        "n_exit_target": int(sum(1 for t in trades if t["why"] == "target")),
        "n_exit_rebalance": int(sum(1 for t in trades if t["why"] == "rebalance")),
        "n_exit_end_of_data": int(sum(1 for t in trades
                                      if t["why"] == "end_of_data")),
        # forecast quality on the traded window (measured here, not imported)
        "pred_label_corr": pred_corr,
        "n_pred_rows": n_pred,
        # the accounting invariant's residual: reported so the artifact shows
        # the ledger closed (a broken ledger raises before this point)
        "pnl_identity_resid": float(resid),
    }
    tables = [dict(kind="symbol", id=sym, **v) for sym, v in sorted(per_sym.items())]
    prov = {"adapter": "xsml", "engine_version": ENGINE_VERSION,
            "fill_model": "taker_next_open",
            "note": "cross-sectional ML book; execution is the repo's, not "
                    "pybroker's (next open, stop first, gap at open, funding at "
                    "real settlements, 11 bps RT per leg); signed-quantity "
                    "ledger with the accounting invariant asserted in-artifact"}
    return metrics, prov, tables
