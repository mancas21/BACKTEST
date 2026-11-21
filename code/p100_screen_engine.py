#!/usr/bin/env python
r"""
p100_screen_engine.py — the repo's execution of the 100-prompt pack, for the
DE-CONTAMINATED RE-SCREEN.

Spec (frozen before any run): results/prompts100_rescreen_pre_registration.md

WHAT THIS IS
------------
The pack's hundred strategies are copied VERBATIM into code/prompts100/ (with
a sha256 manifest) and their SIGNAL LOGIC is used as-is. What this file adds
is the REPO's execution, the repo's metrics, and the repo's accounting
invariant.

    signal  : the pack's own function, unchanged
    book    : the repo's (next open, stop first, gap fills at the open, one
              position at a time, 1% of equity risked at the stop, 20x
              leverage cap, 11 bps round trip per leg, funding charged at the
              real settlements)

THE THREE DECLARED DIFFERENCES FROM THE PACK'S ENGINE
------------------------------------------------------
1. GAP-THROUGH ENTRY. The pack SKIPS a trade whose opening gap has already
   carried price through the stop ("the setup is invalid"). The repo does not
   discard trades: a bad gap is a bad fill, not a trade that never existed.
2. COSTS. The pack's constant is `FEE_PER_SIDE = 0.000055` -- which is 0.55
   bps, not the 5.5 bps its comment and its documentation claim (1 bp =
   1e-4). The pack therefore pays 0.55 bps per side in the fill price AND
   another 0.55 bps as a fee: 1.1 bps round trip, TEN times cheaper than the
   repo's 11 bps standard and a hundred times cheaper than a real Binance perp
   taker round trip. Measured by the parity test.
   The repo pays 11 bps round trip (5 fee + 0.5 slip per side), which is the
   house standard.
3. FUNDING. The pack does not charge funding (except its own family C). The
   repo charges it at the real settlements, on both legs.

The pack's trade PnL also omits the ENTRY fee from the reported PnL (it only
charges it to cash), so its profit factor is not fully ex-cost. Here a trade's
PnL is NET of both fees, so the published PF is truly ex-cost and the
accounting invariant closes.

The accounting invariant is asserted INSIDE every artifact:
    final equity - initial equity == sum(trade pnl) - funding paid
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
PACK = os.path.join(HERE, "prompts100")

ENGINE_VERSION = "p100-screen-1"
INIT = 10_000.0
FEE_BPS = 5.0            # per side
SLIP_BPS = 0.5           # per side
FEE = FEE_BPS / 1e4
SLIP = SLIP_BPS / 1e4
COST_RT_BPS = 2 * (FEE_BPS + SLIP_BPS)
RISK_PCT = 0.01          # 1% of equity risked at the stop, per trade
MAX_LEVERAGE = 20.0      # cap on notional per position

# THE PACK'S REAL COST CONSTANT (its comment says 5.5 bps; 0.000055 is
# 0.55 bps). Used ONLY in pack_conventions mode, to reproduce the pack's
# arithmetic for the parity test.
PACK_COST_PER_SIDE = 0.000055

# ───────────────────────── the two-leg (spread) book ──────────────────────
class SpreadBook:
    """A dollar-neutral pair book, executed with the repo's conventions.

    WHAT THE PACK DOES (kept, and declared)
    ----------------------------------------
    * N units of leg A in the spread's direction and N*beta units of leg B in
      the opposite one; N is sized so that a move of `dist` in the spread
      risks 1% of the equity.
    * the stop lives on the SPREAD. REPO CONVENTION (N5 fix, 2026-11-21):
      detected INTRABAR on the spread's envelope range built from the two
      legs' own high/low (conservative over every leg combination),
      stop-first, gap-through filled at the open -- the same rules as every
      directional book. PACK PARITY MODE (pack_conventions=True) keeps the
      pack's close-detection / next-open-fill semantics, declared as the
      optimistic reading it is.
    * the PnL is the pack's linearised spread PnL: N*side*(spread_exit -
      spread_entry). It is a linearisation: the two legs' exact dollar PnL
      differs from it in the second order.
    * the pack's NOTIONAL for the fee is N*(1+beta). That is NOT the exchange
      notional, which is N*price_A + N*beta*price_B. The report therefore
      publishes BOTH: the cost charged here and the implied exchange notional
      (in multiples of equity), because that second number decides whether
      the book is tradeable at all. The beta used for BOTH side fees is the
      one frozen at entry (N5 fix): a time-varying Kalman beta never bills a
      notional that was not held.

    WHAT THE REPO ADDS
    ------------------
    * 11 bps round trip on the traded notional (the pack's own definition of
      it, at the repo's rate)
    * funding charged at the real settlements, on BOTH legs
    * the accounting invariant asserted inside the artifact
    """

    def __init__(self, legs, sig, *, init=INIT, fee=FEE, slip=SLIP,
                 risk_pct=RISK_PCT, max_leverage=MAX_LEVERAGE,
                 charge_funding=True, pack_conventions=False):
        self.legs = tuple(legs)
        self.tf = sig["tf"]
        self.s = np.asarray(sig["s"], float)
        self.s_open = np.asarray(sig["s_open"], float)
        # N5 FIX (2026-11-21): the spread's INTRABAR range, built by
        # run_pair from the legs' own high/low (conservative envelope over
        # every leg combination). Used by the repo stop convention; absent
        # (pack parity mode) it degrades to the open, which keeps the old
        # close-only behaviour impossible to re-enter accidentally.
        self.s_high = np.asarray(sig.get("s_high", sig["s_open"]), float)
        self.s_low = np.asarray(sig.get("s_low", sig["s_open"]), float)
        self.side_target = np.asarray(sig["side"], float)
        self.stop_s = np.asarray(sig["stop_s"], float)
        self.beta = sig["beta"]
        self.n = len(self.s)
        self.ts = list(sig["ts"])
        self.init = init
        self.fee = fee
        self.slip = slip
        self.risk_pct = risk_pct
        self.max_leverage = max_leverage
        self.pack_conventions = pack_conventions
        self.pnl_includes_funding = False
        self.charge_funding = charge_funding and not pack_conventions
        self.cash = init
        self.equity = init
        self.pos = None
        self.trades = []
        self.equity_curve = []
        self.funding_paid = 0.0
        self.fees_paid = 0.0
        self.entry_fees_total = 0.0
        self.n_signals = 0
        self.n_settlements = 0
        self.implied_notional_x = []      # the exchange notional / equity
        self.leg_bars = {}
        for leg in self.legs:
            self.leg_bars[leg] = load_leg(leg, self.tf)

    def _cost_per_side(self):
        if self.pack_conventions:
            return PACK_COST_PER_SIDE
        return self.fee + self.slip

    def _beta_at(self, j):
        b = self.beta
        if np.isscalar(b):
            return float(b)
        return float(b[j])

    def _leg_price(self, leg, j):
        """The leg's price at bar j (the basket leg has its own index)."""
        lb = self.leg_bars.get(leg)
        if lb is None:
            return None
        idx = lb["idx"].get(int(lb["bar_ms"][j])) if j < len(lb["bar_ms"]) else None
        if idx is None:
            return None
        return float(lb["close"][idx])

    def _funding_cost(self, j):
        """The funding of the two legs at the settlement instants."""
        if self.pos is None:
            return 0.0
        p = self.pos
        total = 0.0
        for leg, qty, sign in p["legs"]:
            lb = self.leg_bars.get(leg)
            if lb is None or j >= len(lb["bar_ms"]):
                continue
            idx = lb["idx"].get(int(lb["bar_ms"][j]))
            if idx is None or not lb["is_fund"][idx] or lb["rate"][idx] == 0:
                continue
            total += sign * qty * lb["close"][idx] * lb["rate"][idx]
        return total

    def _exchange_notional(self, j):
        """The REAL notional of the two legs at bar j (N units of A and
        N*beta of B). This is the number that decides whether the book is
        tradeable; the pack does not use it for its costs."""
        if self.pos is None:
            return None
        p = self.pos
        tot = 0.0
        for leg, qty, _sign in p["legs"]:
            px = self._leg_price(leg, j)
            if px is None:
                return None
            tot += qty * px
        return tot

    def run(self, start_idx=0, end_idx=None, trade_from=None, trade_to=None):
        if end_idx is None:
            end_idx = self.n - 1
        for j in range(start_idx, end_idx + 1):
            tradable = True
            if trade_from is not None and j < trade_from:
                tradable = False
            if trade_to is not None and j > trade_to:
                tradable = False

            # 1. funding on the settlement bar, on BOTH legs (N11 FIX: a
            #    settlement happens at the bar's OPEN instant, BEFORE any
            #    intrabar action -- a stop-out later in the same bar still
            #    owes the funding for the period to that settlement)
            if self.charge_funding and self.pos is not None:
                cost = self._funding_cost(j)
                if cost:
                    self.cash -= cost
                    self.funding_paid += cost

            # 2. the stop on the spread (N5 FIX): under the REPO convention
            #    the stop is detected INTRABAR on the spread's envelope range
            #    (built from the legs' own high/low), stop-first, with a gap
            #    through filled at the open -- the same rules as every
            #    directional book. Under pack_conventions the pack's own
            #    close-detection / next-open-fill semantics are kept.
            stopped = False
            if self.pos is not None and j > self.pos["entry_idx"]:
                if self.pack_conventions:
                    hit = ((self.pos["side"] == 1 and self.s[j] <= self.pos["stop_s"])
                           or (self.pos["side"] == -1
                               and self.s[j] >= self.pos["stop_s"]))
                    if hit:
                        k = j + 1 if j + 1 < self.n else j
                        px = self.s_open[k] if j + 1 < self.n else self.s[j]
                        self._close(k, px, "stop")
                        stopped = True
                else:
                    side, stop = self.pos["side"], self.pos["stop_s"]
                    if side == 1:
                        if self.s_open[j] <= stop:
                            self._close(j, self.s_open[j], "stop_gap")
                            stopped = True
                        elif self.s_low[j] <= stop:
                            self._close(j, stop, "stop")
                            stopped = True
                    else:
                        if self.s_open[j] >= stop:
                            self._close(j, self.s_open[j], "stop_gap")
                            stopped = True
                        elif self.s_high[j] >= stop:
                            self._close(j, stop, "stop")
                            stopped = True

            # 3. mark to market
            if self.pos is not None:
                p = self.pos
                upnl = p["N"] * p["side"] * (self.s[j] - p["entry_s"])
                self.equity_curve.append(self.cash + upnl)
            else:
                self.equity_curve.append(self.cash)

            if j >= end_idx:
                break

            # 4. the desired side after this bar's close
            tgt = self.side_target[j]
            if (not tradable or (trade_from is not None and j + 1 < trade_from)
                    or (trade_to is not None and j + 1 > trade_to)):
                continue
            self.n_signals += 1
            if self.pos is not None and tgt != self.pos["side"]:
                self._close(j + 1, self.s_open[j + 1], "signal")
            if (self.pos is None and not stopped and tgt != 0
                    and np.isfinite(self.stop_s[j])):
                entry_s = self.s_open[j + 1]
                dist = abs(self.stop_s[j] - entry_s)
                if dist > 1e-9:
                    risk = self.cash * self.risk_pct
                    N = min(risk / dist, self.cash * self.max_leverage)
                    beta_j = self._beta_at(j)
                    fee_entry = N * (1 + beta_j) * self._cost_per_side()
                    self.cash -= fee_entry
                    self.fees_paid += fee_entry
                    self.entry_fees_total += fee_entry
                    self.pos = dict(side=int(tgt), N=N, entry_s=entry_s,
                                    stop_s=self.stop_s[j], entry_idx=j + 1,
                                    entry_time=str(self.ts[j + 1]),
                                    fees_entry=fee_entry, risk=risk,
                                    beta=beta_j,
                                    legs=((self.legs[0], N, int(tgt)),
                                          (self.legs[1], N * beta_j, -int(tgt))))
                    notional = self._exchange_notional(j + 1)
                    if notional:
                        self.implied_notional_x.append(notional / self.cash)

        if self.pos is not None:
            self._close(end_idx, self.s[end_idx], "end_of_data")
        if self.equity_curve:
            self.equity_curve[-1] = self.cash
        return self

    def _close(self, idx, exit_s, reason):
        if self.pos is None:
            return None
        p = self.pos
        gross = p["N"] * p["side"] * (exit_s - p["entry_s"])
        # N5 FIX (2026-11-21): the exit fee uses the beta FROZEN AT ENTRY
        # (p["beta"]), the beta the position's legs were actually sized with.
        # The old code charged the beta AT THE EXIT BAR -- with a time-varying
        # Kalman beta that is a notional that was never held.
        fee_exit = p["N"] * (1 + p["beta"]) * self._cost_per_side()
        self.cash += gross - fee_exit
        self.fees_paid += fee_exit
        pnl = gross - fee_exit - p["fees_entry"]
        self.trades.append(dict(entry_idx=p["entry_idx"], exit_idx=idx,
                                entry_time=p["entry_time"],
                                exit_time=str(self.ts[idx]), reason=reason,
                                side="long" if p["side"] == 1 else "short",
                                N=p["N"], entry_s=p["entry_s"], exit_s=exit_s,
                                pnl=pnl,
                                r=(pnl / p["risk"] if p["risk"] else 0.0)))
        self.pos = None
        return self.trades[-1]


def load_leg(symbol, tf):
    """A leg's own bars, for the funding, the mark and the notional.

    The synthetic basket leg (the pack's #88) has no price series of its
    own: it is the equal-weight index of five alts, and its funding is the
    equal-weighted average of theirs.
    """
    if symbol == "ALT-BASKET":
        return None
    df = load_klines(symbol, tf)
    naive = df["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
    bar_ms = (naive.to_numpy().astype("datetime64[ms]").astype("int64"))
    r, e, _n = funding_events(symbol, bar_ms)
    return dict(bar_ms=bar_ms, close=df["close"].to_numpy(float),
                rate=r, is_fund=e,
                idx={int(t): i for i, t in enumerate(bar_ms)})


# ───────────────────────── family B: the pairs and the baskets ───────────
def run_pair(sid, symbol, tf, segment, *, init=INIT, fee=FEE, slip=SLIP,
             charge_funding=True, pack_conventions=False):
    """A spread pair (ids 81, 82, 85, 86, 88, 89): the pack's signal, the
    repo's two-leg book."""
    PS = _pairs_signals()
    sig = PS.pair_signal(sid)
    df_rows = sig["s"]
    ts = pd.to_datetime(pd.Series(sig["ts"]), utc=True)
    df = pd.DataFrame({"timestamp": ts, "open": sig["s_open"],
                       "high": sig["s_open"], "low": sig["s_open"],
                       "close": sig["s"]})
    # N5 FIX (2026-11-21): the spread's INTRABAR range, built from the legs'
    # own high/low. s = log(A) - beta*log(B); the envelope takes the extremes
    # over the four leg-combination candidates, conservative for ANY beta
    # sign. These keys decorate the signal dict ENGINE-SIDE -- the pack's
    # module is untouched (pinned by manifest).
    try:
        ka = load_klines(sig["legs"][0], tf).set_index("timestamp")
        kb = load_klines(sig["legs"][1], tf).set_index("timestamp")
        ts_idx = pd.DatetimeIndex(pd.to_datetime(pd.Series(list(sig["ts"])), utc=True))
        ha = ka["high"].reindex(ts_idx).to_numpy(float)
        la_ = ka["low"].reindex(ts_idx).to_numpy(float)
        hb = kb["high"].reindex(ts_idx).to_numpy(float)
        lb_ = kb["low"].reindex(ts_idx).to_numpy(float)
        beta = np.asarray(sig["beta"], float)
        loga_h, loga_l = np.log(ha), np.log(la_)
        logb_h, logb_l = np.log(hb), np.log(lb_)
        cands = np.stack([
            loga_h - beta * logb_l, loga_h - beta * logb_h,
            loga_l - beta * logb_l, loga_l - beta * logb_h,
        ])
        env_hi = np.nanmax(cands, axis=0)
        env_lo = np.nanmin(cands, axis=0)
        s_open = np.asarray(sig["s_open"], float)
        sig = dict(sig)
        sig["s_high"] = np.where(np.isfinite(env_hi), env_hi, s_open)
        sig["s_low"] = np.where(np.isfinite(env_lo), env_lo, s_open)
        df["high"] = sig["s_high"]
        df["low"] = sig["s_low"]
    except Exception:
        # envelope unavailable: degrade to the pack's zero-range frame
        # (declared; the stop model then equals the pack parity mode)
        pass
    book = SpreadBook(sig["legs"], sig, init=init, fee=fee, slip=slip,
                      charge_funding=charge_funding,
                      pack_conventions=pack_conventions)
    seg = _segment_bounds_idx(sig["ts"], segment)
    book.run(start_idx=seg["start"], end_idx=seg["end"],
             trade_from=seg["trade_from"], trade_to=seg["trade_to"])
    return book, sig


def _segment_bounds_idx(ts_list, segment):
    """The screen's segments, applied to a timestamp list."""
    ts = pd.to_datetime(pd.Series(list(ts_list)), utc=True)
    dev_end = pd.Timestamp(DEV_END, tz="UTC")
    purge_end = pd.Timestamp(PURGE_END, tz="UTC")
    oos_start = pd.Timestamp(OOS_START, tz="UTC")
    if segment == "DEV":
        idx = np.where(ts < dev_end)[0]
        if not len(idx):
            raise ValueError("sin datos DEV")
        return dict(start=int(idx[0]), end=int(idx[-1]),
                    trade_from=int(idx[0]), trade_to=int(idx[-1]))
    if segment == "OOS":
        idx = np.where(ts >= oos_start)[0]
        if not len(idx):
            raise ValueError("sin datos OOS")
        purge = np.where((ts >= dev_end) & (ts < purge_end))[0]
        trade_from = int(purge[-1]) + 1 if len(purge) else int(idx[0])
        return dict(start=int(idx[0]), end=int(idx[-1]),
                    trade_from=trade_from, trade_to=int(idx[-1]))
    raise ValueError(f"segmento desconocido: {segment}")


def run_basket(sid, symbol, tf, segment, *, init=INIT, fee=FEE, slip=SLIP,
               charge_funding=True, pack_conventions=False):
    """A cross-sectional basket (ids 83, 84, 87, 90): the pack's ranking and
    weights, the repo's book (11 bps on the turnover, funding on every leg)."""
    PS = _pairs_signals()
    sig = PS.basket_signal(sid)
    symbols = sig["symbols"]
    closes = sig["closes"]
    opens = sig["opens"]
    rets = sig["rets"]
    signal = sig["signal"]
    top_k = sig["top_k"]
    rebal = sig["rebalance_bars"]

    ts = pd.to_datetime(pd.Series(sig["ts"]), utc=True)
    n = len(ts)
    seg = _segment_bounds_idx(sig["ts"], segment)
    start, end = seg["start"], seg["end"]

    # the legs' own bars, for the funding
    leg_fund = {}
    for sym in symbols:
        df = load_klines(sym, sig["tf"])
        naive = df["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
        bm = (naive.to_numpy().astype("datetime64[ms]").astype("int64"))
        r, e, _n = funding_events(sym, bm)
        leg_fund[sym] = dict(bar_ms=bm, rate=r, is_fund=e,
                             idx={int(t): i for i, t in enumerate(bm)})

    cash = float(init)
    equity_curve = []
    weights = {s: 0.0 for s in symbols}
    last_rebal = -10 ** 9
    trades = []
    fees_paid = 0.0
    funding_paid = 0.0
    pending_start = cash
    cost = PACK_COST_PER_SIDE if pack_conventions else (fee + slip)

    def leg_funding_cost(j):
        total = 0.0
        for sym in symbols:
            w = weights[sym]
            if w == 0.0:
                continue
            lb = leg_fund[sym]
            if j >= len(lb["bar_ms"]):
                continue
            idx = lb["idx"].get(int(lb["bar_ms"][j]))
            if idx is None or not lb["is_fund"][idx] or lb["rate"][idx] == 0:
                continue
            # the leg's NOTIONAL is w * equity (the weight is a fraction of
            # the book, not a number of units), so the funding is that
            # notional times the rate -- NOT multiplied by the price.
            total += w * cash * lb["rate"][idx]
        return total

    def do_rebalance(j):
        nonlocal cash, last_rebal, fees_paid
        avail = [s for s in symbols
                 if np.isfinite(signal[s][j]) and np.isfinite(closes[s][j])]
        if len(avail) < 2 * top_k:
            return 0.0
        ranked = sorted(avail, key=lambda s: signal[s][j])
        if sig["mode"] == "lowvol":
            longs, shorts = ranked[:top_k], ranked[-top_k:]
        else:
            longs, shorts = ranked[-top_k:], ranked[:top_k]
        new_w = {s: 0.0 for s in symbols}
        leg = 1.0 / (2 * top_k)
        for s in longs:
            new_w[s] = leg
        for s in shorts:
            new_w[s] = -leg
        turnover = sum(abs(new_w[s] - weights[s]) for s in symbols)
        f = turnover * cash * cost
        cash -= f
        fees_paid += f
        weights.update(new_w)
        last_rebal = j
        return f

    period_pnl = 0.0            # the DOLLAR change of the current period
    for j in range(max(1, start), end + 1):
        pnl = 0.0
        for s in symbols:
            r = rets[s][j]
            if weights[s] != 0.0 and np.isfinite(r):
                pnl += weights[s] * r
        before = cash
        cash *= (1 + pnl)
        period_pnl += cash - before
        if charge_funding:
            fc = leg_funding_cost(j)
            if fc:
                cash -= fc
                funding_paid += fc
                period_pnl -= fc
        equity_curve.append(cash)
        if j - last_rebal >= rebal:
            if last_rebal > -10 ** 8:
                trades.append(dict(entry_idx=last_rebal, exit_idx=j,
                                  pnl=period_pnl,
                                  r=(period_pnl / pending_start)
                                  if pending_start else 0.0,
                                  reason="basket"))
            fee = do_rebalance(j)
            pending_start = cash
            period_pnl = -fee     # the cost of THIS rebalance belongs to the
                                  # period it opens

    if last_rebal > -10 ** 8:
        trades.append(dict(entry_idx=last_rebal, exit_idx=end,
                           pnl=period_pnl,
                           r=(period_pnl / pending_start) if pending_start else 0.0,
                           reason="basket"))

    class _B:            # a tiny carrier with the same fields as Book
        pass

    b = _B()
    b.trades = trades
    b.equity_curve = equity_curve
    b.cash = cash
    b.init = init
    b.fees_paid = fees_paid
    b.funding_paid = funding_paid
    b.entry_fees_total = 0.0
    b.pack_conventions = pack_conventions
    b.pnl_includes_funding = True
    b.n_settlements = 0
    b.n_signals = len(trades)
    b.skipped_gap_entries = 0
    return b, sig


# The screen's segments (results/prompts100_rescreen_pre_registration.md):
# DEV for the selection, a purge month with no trading, OOS for the verdict.
DEV_END = "2025-10-01"
PURGE_END = "2025-10-31"
OOS_START = "2025-11-01"

MIN_DEV_TRADES = 30      # below this the strategy is INSUFFICIENT SAMPLE

# the pair and basket prompts (family B): a different book shape
SPREAD_IDS = (81, 82, 85, 86, 88, 89)
BASKET_IDS = (83, 84, 87, 90)
# each pair prompt's own two legs and timeframe (from the pack's own code)
PAIR_LEGS = {81: ("SOLUSDT", "1h"), 82: ("BTCUSDT", "1h"),
             85: ("HYPEUSDT", "1h"), 86: ("SUIUSDT", "1h"),
             88: ("BTCUSDT", "1h"), 89: ("ETHUSDT", "15m")}

TF_DIRS = {"1h": "binance_klines_1h", "15m": "binance_klines_15m",
            "5m": "binance_klines_5m"}


# ───────────────────────── the pack, imported verbatim ─────────────────────
def _load_pack():
    if PACK not in sys.path:
        sys.path.insert(0, PACK)
    import backtest100_strategies as S          # noqa: E402
    import backtest100_engine as E             # noqa: E402
    return S, E


def _pairs_signals():
    """The pair/basket signal module (code/prompts100/pairs_signals.py)."""
    import importlib.util
    p = os.path.join(PACK, "pairs_signals.py")
    spec = importlib.util.spec_from_file_location("p100_pairs_signals", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pack_manifest():
    p = os.path.join(PACK, "MANIFEST.json")
    return json.load(open(p, encoding="utf-8"))


def verify_pack_copy():
    """The ported copy must still match the manifest: if someone edits the
    pack's code in the repo, the parity proof stops meaning anything."""
    man = pack_manifest()
    bad = []
    for fn, meta in man["files"].items():
        p = os.path.join(PACK, fn)
        if not os.path.exists(p):
            bad.append(f"{fn}: falta")
            continue
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest() != meta["sha256"]:
            bad.append(f"{fn}: sha distinto")
    return (not bad), bad


def pack_strategy_map():
    """The pack's own id -> (symbol, tf) map, read from the ported runner.

    The map is the pack's, not ours: a prompt is bound to its symbol and
    timeframe, and the engine REFUSES any other combination (the same rule
    the `top10` adapter applies).
    """
    p = os.path.join(PACK, "backtest100_runner.py")
    src = open(p, encoding="utf-8", errors="replace").read()
    i = src.find("STRATEGY_MAP = {")
    j = src.find("\n}", i)
    block = src[i:j + 2]
    return ast.literal_eval(block[block.index("{"):])


# ───────────────────────────── data ───────────────────────────────────────
# N6 FIX (2026-11-21): the harness serves the CUT SLICE of every declared
# input from a temp directory (same basenames). This engine used to resolve
# its own paths and read the LIVE file while the artifact hashed the slice --
# the cut protected nothing. run_symbol registers the served paths below and
# load_klines / funding_events consult them first, so the engine reads
# exactly the bytes the artifact hashes.
_SERVED_INPUTS = {}


def _register_served(paths):
    _SERVED_INPUTS.clear()
    for x in (paths or []):
        try:
            _SERVED_INPUTS[os.path.basename(str(x))] = os.path.abspath(str(x))
        except Exception:
            pass


def load_klines(symbol: str, tf: str):
    p = os.path.join(ROOT, "data", TF_DIRS[tf], f"{symbol}_{tf}.csv")
    p = _SERVED_INPUTS.get(os.path.basename(p), p)
    df = pd.read_csv(p)
    df.columns = [c.strip().lower() for c in df.columns]
    ts_col = "timestamp" if "timestamp" in df.columns else "open_ts"
    df["timestamp"] = pd.to_datetime(df[ts_col], unit="ms", utc=True)
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    return df.reset_index(drop=True)


def funding_events(symbol: str, bar_ms: np.ndarray):
    """(rate, is_event) per bar, repo convention: a settlement at t maps to
    the first bar whose OPEN is at or after t.

    F2 FIX: rates ACCUMULATE on a bar. When the bar interval exceeds the funding
    interval (e.g. 1d bars vs 8h/4h funding) several settlements map to the same
    bar; the old `rate[j] = r` kept only the LAST and under-charged funding by
    ~2-5x on coarse timeframes. Intraday bars (interval < funding interval) have
    no collision, so their results are unchanged."""
    p = os.path.join(ROOT, "data", "binance_funding", f"{symbol}_funding.json")
    p = _SERVED_INPUTS.get(os.path.basename(p), p)
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
            rate[j] += float(x["r"])   # F2: accumulate, do not overwrite
            n += 1
    return rate, ev, n


# ───────────────────────── the repo's execution ───────────────────────────
class Book:
    """One position at a time, with the repo's conventions.

    F17 DECLARED LIMITATION: cash accounting is fully-funded synthetic (entry
    debits qty*fill, so cash can go negative for a levered long while MTM nets
    out). There is NO intra-bar margin-call / liquidation simulation; a real
    perp can liquidate on a gap before the stop fills. Liquidation is guarded
    only post-hoc by gate G9 (per-trade MAE vs 1/leverage - mmr). Any levered
    verdict must state this limitation."""

    def __init__(self, symbol, tf, df, *, init=INIT, fee=FEE, slip=SLIP,
                 risk_pct=RISK_PCT, max_leverage=MAX_LEVERAGE,
                 charge_funding=True, pack_conventions=False):
        self.symbol = symbol
        self.tf = tf
        self.df = df.reset_index(drop=True)
        self.n = len(self.df)
        self.open = self.df["open"].to_numpy(float)
        self.high = self.df["high"].to_numpy(float)
        self.low = self.df["low"].to_numpy(float)
        self.close = self.df["close"].to_numpy(float)
        self.ts = self.df["timestamp"]
        # epoch milliseconds, WITHOUT the pandas-3 unit trap: `astype` on a
        # tz-aware column raises (and its int64 unit is not always ms), so
        # the timezone is dropped explicitly first.
        naive = self.ts.dt.tz_convert("UTC").dt.tz_localize(None)
        self.bar_ms = (naive.to_numpy().astype("datetime64[ms]")
                       .astype("int64"))
        self.init = init
        self.fee = fee
        self.slip = slip
        self.risk_pct = risk_pct
        self.max_leverage = max_leverage
        # PACK CONVENTIONS MODE: reproduce the pack's own engine (its cost in
        # the price AND as a fee, the gap-through ENTRY skipped, no funding,
        # and the trade PnL without the entry fee). Used ONLY by the parity
        # test.
        self.pack_conventions = pack_conventions
        self.pnl_includes_funding = False
        self.charge_funding = charge_funding and not pack_conventions
        self.cash = init
        self.equity = init
        self.pos = None                  # dict: side, qty, fill, stop, tp, ...
        self.trades = []
        self.equity_curve = []
        self.funding_paid = 0.0
        self.fees_paid = 0.0
        self.entry_fees_total = 0.0
        self.skipped_gap_entries = 0
        self.n_signals = 0
        r, e, self.n_settlements = funding_events(symbol, self.bar_ms)
        self.rate, self.is_fund = r, e

    # -- fills -------------------------------------------------------------
    def _fill_px(self, px, side):
        """Price the trade happens at. The repo: slippage against the book.
        The pack: its own cost constant folded into the price."""
        if self.pack_conventions:
            return px * (1 + side * PACK_COST_PER_SIDE)
        return px * (1 + side * self.slip)

    def _fee(self, notional):
        if self.pack_conventions:
            # the pack charges its cost in the PRICE and again as a fee
            return notional * PACK_COST_PER_SIDE
        return notional * self.fee

    def open_position(self, idx, side, stop_px, tp_px=None, max_hold=None):
        """Open at the OPEN of bar idx (the signal was on bar idx-1)."""
        if self.pos is not None:
            return False
        fill = self._fill_px(self.open[idx], side)
        if self.pack_conventions:
            # the pack refuses a trade whose opening gap already crossed the
            # stop (or the target): the setup is "invalid"
            if side == 1:
                if fill <= stop_px:
                    self.skipped_gap_entries += 1
                    return False
                if tp_px is not None and fill >= tp_px:
                    self.skipped_gap_entries += 1
                    return False
            else:
                if fill >= stop_px:
                    self.skipped_gap_entries += 1
                    return False
                if tp_px is not None and fill <= tp_px:
                    self.skipped_gap_entries += 1
                    return False
        dist = abs(stop_px - self.open[idx])
        if dist <= 0:
            return False
        risk_amount = self.equity * self.risk_pct
        qty = risk_amount / dist
        # the pack caps the notional against the FILLED price (the cost is
        # inside it); the repo caps it against the open
        cap_ref = fill if self.pack_conventions else self.open[idx]
        max_qty = self.max_leverage * self.equity / cap_ref
        if qty > max_qty:
            qty = max_qty
        notional = qty * fill          # the fee is charged on the traded
        fee = self._fee(notional)     # notional, WITH the fill price
        if side == 1:
            self.cash -= qty * fill + fee
        else:
            self.cash += qty * fill - fee
        self.fees_paid += fee
        self.entry_fees_total += fee
        self.pos = dict(side=side, qty=qty, fill=fill, stop=stop_px, tp=tp_px,
                        entry_idx=idx, entry_ms=int(self.bar_ms[idx]),
                        entry_ts=str(self.ts.iloc[idx]), risk=risk_amount,
                        max_hold=max_hold, fee_in=fee)
        return True

    def close_position(self, idx, exit_px, reason):
        if self.pos is None:
            return None
        p = self.pos
        fill = self._fill_px(exit_px, -p["side"])   # selling a long, buying back
        notional = p["qty"] * fill
        fee = self._fee(notional)
        if p["side"] == 1:
            pnl = p["qty"] * (fill - p["fill"]) - fee
            self.cash += p["qty"] * fill - fee
        else:
            pnl = p["qty"] * (p["fill"] - fill) - fee
            self.cash -= p["qty"] * fill + fee
        if not self.pack_conventions:
            # THE REPO'S RULE: a trade's PnL is NET of BOTH fees. The pack
            # omits the entry fee from the trade PnL (it only charges it to
            # cash), which inflates its profit factor: the cash and the
            # reported PnL do not describe the same money. Here the entry fee
            # is deducted as well, so the accounting invariant closes and the
            # published PF is truly ex-cost.
            pnl -= p["fee_in"]
        self.fees_paid += fee
        self.equity = self.cash
        self.trades.append(dict(
            entry_idx=p["entry_idx"], exit_idx=idx,
            entry_time=p["entry_ts"], exit_time=str(self.ts.iloc[idx]),
            side="long" if p["side"] == 1 else "short",
            qty=p["qty"], entry=p["fill"], exit=fill, pnl=pnl, fee=fee,
            r=(pnl / p["risk"] if p["risk"] else 0.0), reason=reason))
        self.pos = None
        return self.trades[-1]

    def mark_to_market(self, idx):
        if self.pos is None:
            return self.cash
        p = self.pos
        if p["side"] == 1:
            return self.cash + p["qty"] * self.close[idx]
        return self.cash - p["qty"] * self.close[idx]

    # -- the loop ----------------------------------------------------------
    def run(self, signal_fn, start_idx=0, end_idx=None, trade_from=None,
            trade_to=None):
        """Run the book.

        signal_fn(j) -> None | {"side": +1/-1/0, "stop_px", "tp_px", "max_hold"}
        trade_from / trade_to: the bars in which the book MAY trade (the
        purge zone is outside them, and the book is flat there).
        """
        if end_idx is None:
            end_idx = self.n - 1
        for j in range(start_idx, end_idx + 1):
            tradable = True
            if trade_from is not None and j < trade_from:
                tradable = False
            if trade_to is not None and j > trade_to:
                tradable = False

            # 1. funding on the settlement bar (N11 FIX, 2026-11-21: a
            #    settlement happens at the bar's OPEN instant, BEFORE any
            #    intrabar action -- a stop-out later in the same bar still
            #    owes the funding for the period to that settlement. The old
            #    order let ~1/8 of 1h stop-outs escape their settlement.)
            if self.charge_funding and self.pos is not None \
                    and self.is_fund[j] and self.rate[j] != 0:
                mark = self.close[j]
                cost = self.pos["side"] * self.pos["qty"] * mark * self.rate[j]
                self.cash -= cost
                self.funding_paid += cost

            # 2. time stop
            if self.pos is not None and self.pos["max_hold"] is not None:
                if j - self.pos["entry_idx"] >= self.pos["max_hold"]:
                    self.close_position(j, self.open[j], "time")

            # 3. stop / target intrabar (STOP FIRST), gap fills at the open
            if self.pos is not None:
                p = self.pos
                hi, lo, op = self.high[j], self.low[j], self.open[j]
                if p["side"] == 1:
                    if op <= p["stop"]:
                        self.close_position(j, op, "stop_gap")
                    elif lo <= p["stop"]:
                        self.close_position(j, p["stop"], "stop")
                    elif p["tp"] is not None and hi >= p["tp"]:
                        self.close_position(j, p["tp"], "tp")
                else:
                    if op >= p["stop"]:
                        self.close_position(j, op, "stop_gap")
                    elif hi >= p["stop"]:
                        self.close_position(j, p["stop"], "stop")
                    elif p["tp"] is not None and lo <= p["tp"]:
                        self.close_position(j, p["tp"], "tp")

            # 4. equity at the close of the bar
            self.equity = self.mark_to_market(j)
            self.equity_curve.append(self.equity)

            if j >= end_idx:
                break

            # 5. the signal on this bar fills at the OPEN of the next one
            if not tradable or (trade_from is not None and j + 1 < trade_from):
                continue
            if trade_to is not None and j + 1 > trade_to:
                continue
            sig = signal_fn(j)
            if sig is None:
                continue
            self.n_signals += 1
            side = int(sig.get("side", 0))
            if side == 0:
                if self.pos is not None:
                    self.close_position(j + 1, self.open[j + 1], "signal")
                continue
            stop_px = sig.get("stop_px")
            if stop_px is None:
                continue
            # An OPPOSITE-side signal reverses the open position at the same
            # next open (the pack's signal semantics: the signal carries the
            # direction, so a flip is a flip, not a no-op).
            if self.pos is not None and side != self.pos["side"]:
                self.close_position(j + 1, self.open[j + 1], "reverse")
            self.open_position(j + 1, side, stop_px, sig.get("tp_px"),
                               sig.get("max_hold"))

        # end of the segment: force close at that bar's close
        if self.pos is not None:
            self.close_position(end_idx, self.close[end_idx], "end_of_data")
        if self.equity_curve:
            self.equity_curve[-1] = self.cash
        return self


# ───────────────────────── segments ───────────────────────────────────────
def segment_bounds(df, segment):
    """The screen's segments (frozen in the pre-registration)."""
    ts = df["timestamp"]
    dev_end = pd.Timestamp(DEV_END, tz="UTC")
    purge_end = pd.Timestamp(PURGE_END, tz="UTC")
    oos_start = pd.Timestamp(OOS_START, tz="UTC")
    if segment == "DEV":
        idx = np.where(ts < dev_end)[0]
        if not len(idx):
            raise ValueError("sin datos DEV")
        start, end = int(idx[0]), int(idx[-1])
        return dict(start=start, end=end, trade_from=start, trade_to=end)
    if segment == "OOS":
        idx = np.where(ts >= oos_start)[0]
        if not len(idx):
            raise ValueError("sin datos OOS")
        start, end = int(idx[0]), int(idx[-1])
        purge = np.where((ts >= dev_end) & (ts < purge_end))[0]
        trade_from = int(purge[-1]) + 1 if len(purge) else start
        return dict(start=start, end=end, trade_from=trade_from, trade_to=end)
    if segment == "FULL":
        return dict(start=0, end=len(df) - 1, trade_from=0,
                    trade_to=len(df) - 1)
    raise ValueError(f"segmento desconocido: {segment}")


# ───────────────────────── the family's books ──────────────────────────────
def run_family_a(strategy_id, symbol, tf, segment, *, init=INIT, fee=FEE,
                 slip=SLIP, charge_funding=True, pack_conventions=False):
    """Family A: one symbol, the pack's signal function, the repo's book."""
    S, _E = _load_pack()
    fn = S.STRATEGIES.get(str(strategy_id))
    if fn is None:
        raise ValueError(f"estrategia {strategy_id} sin implementacion")
    df = load_klines(symbol, tf)
    ctx = S.LazyCtx(df)
    seg = segment_bounds(df, segment)
    book = Book(symbol, tf, df, init=init, fee=fee, slip=slip,
                charge_funding=charge_funding,
                pack_conventions=pack_conventions)

    def signal(j):
        return fn(j, ctx)

    book.run(signal, start_idx=seg["start"], end_idx=seg["end"],
             trade_from=seg["trade_from"], trade_to=seg["trade_to"])
    return book, ctx


# ───────────────────────── metrics ─────────────────────────────────────────
def bootstrap_r(rs, block=None, n_boot=2000, seed=20261101, min_n=30):
    """Block bootstrap of the mean R per trade (the repo's recipe).

    N7 FIX (2026-11-21): the block length used to be the FIXED constant 10,
    so for n <= 10 the start range collapsed to {0}, one block covered the
    whole sample and the CI was zero-width -- `ci_low > 0` then passed
    deterministically for any all-positive small sample. The block now
    scales with n (n**(1/3), the repo's own _gates_v2._block_len recipe) and
    the result FAILS CLOSED below the n floor: ci_low is reported as -inf
    (never passable) with a flag, instead of a degenerate interval."""
    rs = np.asarray(rs, float)
    rs = rs[np.isfinite(rs)]
    if len(rs) == 0:
        return dict(ci_low=0.0, ci_high=0.0, t_stat=0.0, mean_r=0.0, n_boot=n_boot,
                    n=0, small_sample=True)
    rng = np.random.default_rng(seed)
    mean_r = float(rs.mean())
    n = len(rs)
    small = bool(n < min_n)
    if block is None:
        block = int(max(1, round(n ** (1.0 / 3.0))))
    block = int(min(max(1, block), n))
    means = []
    for _ in range(n_boot):
        starts = rng.integers(0, max(1, n - block + 1), size=max(1, n // block))
        samp = np.concatenate([rs[s:s + block] for s in starts])[:n]
        means.append(float(samp.mean()))
    means = np.array(means)
    lo = float(np.percentile(means, 2.5))
    hi = float(np.percentile(means, 97.5))
    t_stat = (mean_r / (float(rs.std(ddof=1)) / np.sqrt(n))
              if n > 1 and rs.std(ddof=1) > 0 else 0.0)
    # N7: fail closed on a thin sample -- a degenerate CI must never pass.
    # Finite sentinel (-1.0, JSON-safe) so the boot_ci gate fails arithmetically.
    return dict(ci_low=(-1.0 if small else lo),
                ci_high=(1.0 if small else hi),
                t_stat=float(t_stat), mean_r=mean_r, n_boot=n_boot,
                n=int(n), small_sample=small)


def book_metrics(book, *, bh_return_pct=None):
    """The repo's metrics, computed FROM the book's ledger."""
    pnls = np.array([t["pnl"] for t in book.trades], float)
    n = len(pnls)
    gp = float(pnls[pnls > 0].sum()) if n else 0.0
    gl = float(-pnls[pnls < 0].sum()) if n else 0.0
    pf = (gp / gl) if gl > 0 else (None if gp > 0 else 0.0)
    eq = np.array(book.equity_curve, float)
    eq = eq[np.isfinite(eq)]
    peak = np.maximum.accumulate(eq) if len(eq) else np.array([book.init])
    mdd = float((eq / peak - 1).min()) if len(eq) else 0.0
    net = float(book.cash / book.init - 1)
    pnl_sum = float(pnls.sum()) if n else 0.0

    # ACCOUNTING INVARIANT: final equity - initial equity must equal the sum
    # of the net trade PnL minus the funding paid. Asserted here so a broken
    # ledger fails loudly instead of producing a plausible-looking PF.
    # In the pack's own mode the trade PnL omits the entry fee (that IS the
    # pack's arithmetic), so the identity carries it explicitly.
    if getattr(book, "pack_conventions", False):
        resid = ((book.cash - book.init)
                 - (pnl_sum - book.funding_paid - book.entry_fees_total))
    elif getattr(book, "pnl_includes_funding", False):
        # the basket's trade PnL already carries the funding (it is a real
        # cost of holding the leg), so it is not subtracted twice
        resid = (book.cash - book.init) - pnl_sum
    else:
        resid = (book.cash - book.init) - (pnl_sum - book.funding_paid)
    if abs(resid) > max(1e-6, abs(pnl_sum) * 1e-9):
        raise AssertionError(
            f"accounting invariant broken: cash-INIT={book.cash - book.init:.8f} "
            f"vs sum(pnl)-funding={pnl_sum - book.funding_paid:.8f} "
            f"(residual {resid:.8f})")

    thirds = []
    if len(eq):
        for i in range(3):
            a = len(eq) * i // 3
            b = len(eq) * (i + 1) // 3
            thirds.append(100.0 * (eq[b - 1] / eq[a] - 1)
                          if b > a and eq[a] > 0 else 0.0)
    else:
        thirds = [0.0, 0.0, 0.0]

    if n:
        srt = np.sort(pnls)[::-1]
        best5 = float(srt[:5].sum())
        top5_share = (100.0 * best5 / pnl_sum) if pnl_sum > 0 else None
        net_wo5 = 100.0 * (pnl_sum - best5) / book.init
        rest = srt[5:]
        g5 = float(rest[rest > 0].sum())
        l5 = float(-rest[rest < 0].sum())
        pf_wo5 = (g5 / l5) if l5 > 0 else None
    else:
        top5_share, net_wo5, pf_wo5 = None, None, None

    boot = bootstrap_r([t["r"] for t in book.trades])

    metrics = {
        "return_pct": 100 * net,
        "profit_factor": pf,
        "n_trades": int(n),
        "win_rate": 100 * float((pnls > 0).sum() / n) if n else 0.0,
        "max_dd_pct": 100 * mdd,
        "final_equity": float(book.cash),
        "init_equity": book.init,
        "cost_bp_roundtrip": COST_RT_BPS,
        # the pack's OWN cost constant, measured here so the report can cite
        # it with a run_id instead of asserting it in prose
        "pack_cost_per_side_bps": PACK_COST_PER_SIDE * 1e4,
        "pack_cost_roundtrip_bps": 4 * PACK_COST_PER_SIDE * 1e4,
        "pack_cost_constant": PACK_COST_PER_SIDE,
        "fees_paid_usdt": float(book.fees_paid),
        "funding_paid_usdt": float(book.funding_paid),
        "n_settlements": int(getattr(book, "n_settlements", 0)),
        "funding_charged": bool(getattr(book, "charge_funding", False)),
        "gross_profit_usdt": gp,
        "gross_loss_usdt": gl,
        # N1 FIX: the CANONICAL unit-named key (percent). The old
        # top5_pnl_share name is AMBIGUOUS across adapters (some store a
        # fraction) and bt one now refuses it; this engine emits both, with
        # the canonical key carrying the same percent value.
        "top5_pnl_share": top5_share,
        "conc_top5_share_pct": top5_share,
        "net_without_top5_pct": net_wo5,
        "pf_without_top5": pf_wo5,
        "period1_pct": thirds[0],
        "period2_pct": thirds[1],
        "period3_pct": thirds[2],
        "n_periods_green": int(sum(1 for t in thirds if t > 0)),
        "boot_ci_lo": float(boot["ci_low"]),
        "boot_ci_hi": float(boot["ci_high"]),
        "boot_t_stat": float(boot["t_stat"]),
        "boot_mean_r": float(boot["mean_r"]),
        "boot_n": int(boot["n_boot"]),
        # N7: the thin-sample flag travels with the CI so a sentinel-failed
        # gate is explainable from the artifact alone
        "boot_small_sample": bool(boot.get("small_sample", False)),
        "boot_trades_n": int(boot.get("n", 0)),
        "n_signals": int(getattr(book, "n_signals", 0)),
        "n_skipped_gap_entries": int(getattr(book, "skipped_gap_entries", 0)),
        "n_exits_stop": int(sum(1 for t in book.trades
                                if t["reason"] in ("stop", "stop_gap"))),
        "n_exits_target": int(sum(1 for t in book.trades
                                  if t["reason"] in ("tp", "basket"))),
        "n_exits_signal": int(sum(1 for t in book.trades
                                   if t["reason"] == "signal")),
        "n_exits_reverse": int(sum(1 for t in book.trades
                                    if t["reason"] == "reverse")),
        "n_exits_time": int(sum(1 for t in book.trades if t["reason"] == "time")),
        "n_exits_end": int(sum(1 for t in book.trades
                               if t["reason"] == "end_of_data")),
        "pnl_identity_resid": float(resid),
    }
    implied = getattr(book, "implied_notional_x", None)
    if implied:
        arr = np.array(implied, float)
        metrics["implied_notional_x_median"] = float(np.median(arr))
        metrics["implied_notional_x_max"] = float(arr.max())
        # what the repo's cost regime would charge on the REAL exchange
        # notional (the pack charges on its own, much smaller, definition)
        metrics["cost_on_real_notional_usdt"] = float(
            arr.mean() * COST_RT_BPS / 1e4 * book.init)
    if bh_return_pct is not None:
        metrics["bh_return_pct"] = float(bh_return_pct)
        metrics["excess_pct"] = float(100 * net - bh_return_pct)
    return metrics


def buy_and_hold_pct(df, segment):
    """Buy and hold over the segment (the benchmark every book is measured
    against)."""
    seg = segment_bounds(df, segment)
    a = df["close"].to_numpy(float)
    i0, i1 = seg["trade_from"], seg["trade_to"]
    if i1 <= i0:
        return None
    return 100.0 * (a[i1] / a[i0] - 1.0)


# ───────────────────────── adapter entry point ─────────────────────────────
# ─────────────────────── N9: per-symbol gate cost ─────────────────────────
def _resolve_gate_cost(symbols):
    """(fee_bps, slip_bps, rt_bps, source): the repo rule -- gate cost is the
    MAX of the repo default round trip and the symbol's MEASURED round trip
    (results/cost_model_2026-10-25.json), fee 5 bps, slip = rt/2 - fee.
    Mirrors _gates_v2.resolve_gate_cost; for a multi-leg book the MAX leg
    cost is charged on every leg (conservative)."""
    import importlib.util
    rt = 11.0
    src = "repo default"
    model = None
    cm = os.path.join(ROOT, "results", "cost_model_2026-10-25.json")
    if os.path.exists(cm):
        try:
            # load _gates_v2 from THIS file's directory (the harness may run
            # the engine with an isolated sys.path; a bare import would fail).
            # The module MUST be registered in sys.modules before exec --
            # dataclass resolution inside _gates_v2 looks its own module up.
            name = "_gates_v2_for_cost"
            spec = importlib.util.spec_from_file_location(
                name,
                os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "_gates_v2.py"))
            GV = importlib.util.module_from_spec(spec)
            sys.modules[name] = GV
            spec.loader.exec_module(GV)
            model = GV.load_cost_model(cm)
        except Exception:
            model = None
    for s in (symbols or []):
        m = (model or {}).get(s.upper())
        if m is not None and m > rt:
            rt = m
            src = f"measured ({s})"
    fee = 5.0
    slip = rt / 2.0 - fee
    return fee, slip, rt, src


def _symbols_from_paths(paths):
    """The symbols the book touches, from the served inputs' basenames."""
    import re
    syms = set()
    for x in (paths or []):
        b = os.path.basename(str(x))
        m = re.match(r"([A-Z0-9]{3,12}USDT)_", b)
        if m:
            syms.add(m.group(1))
    return sorted(syms)


def run_symbol(paths, params):
    """Harness contract: (metrics, prov, tables)."""
    p = dict(params)
    sid = int(p.pop("id"))
    segment = str(p.pop("segment", "DEV"))
    # N6 FIX (2026-11-21): consume the SERVED inputs (the cut slice the
    # artifact hashes), not the live files this engine used to re-resolve.
    _register_served(paths)
    # N9 FIX (2026-11-21): the gate cost for a thin name is its MEASURED
    # round trip (results/cost_model_2026-10-25.json via the repo resolver),
    # not the flat 11 bps default -- SPX was being backtested at 36% of its
    # real cost. Explicit fee/slip params still win (parity probes, zero-cost
    # controls); the resolved values are measured inside the artifact.
    fee_bps, slip_bps, rt_bps, cost_src = _resolve_gate_cost(
        _symbols_from_paths(paths))
    if "fee_bps" in p:
        fee_bps = float(p.pop("fee_bps"))
        cost_src = "declared by caller"
    if "slip_bps" in p:
        slip_bps = float(p.pop("slip_bps"))
    fee = fee_bps / 1e4
    slip = slip_bps / 1e4
    charge_funding = bool(p.pop("funding", True))
    pack_conventions = bool(p.pop("pack_conventions", False))
    symbol = str(p.pop("symbol", "") or "")
    tf = str(p.pop("tf", "") or "")
    if p:
        raise ValueError(f"unknown p100 screen params: {sorted(p)}")

    # The prompt is bound to the pack's own symbol and timeframe: the engine
    # refuses any other combination.
    smap = pack_strategy_map()
    bound = smap.get(str(sid))
    if sid in SPREAD_IDS:
        want_symbol, want_tf = PAIR_LEGS[sid]
    elif sid in BASKET_IDS:
        want_symbol, want_tf = "BASKET6", "1h"
    elif bound is not None:
        want_symbol, want_tf = bound
    else:
        raise ValueError(f"p100 screen: el prompt {sid} no esta en el mapa "
                         f"del pack")
    if not symbol or not tf:
        base = os.path.basename(paths[0])
        stem = base[:-4]
        symbol, tf = stem.rsplit("_", 1)
    if sid not in SPREAD_IDS and sid not in BASKET_IDS:
        if (symbol, tf) != (want_symbol, want_tf):
            raise ValueError(
                f"p100 screen: el prompt {sid} esta atado a {want_symbol} "
                f"{want_tf}, no a {symbol} {tf}")

    if sid in SPREAD_IDS:
        book, ctx = run_pair(sid, symbol, tf, segment, fee=fee, slip=slip,
                             charge_funding=charge_funding,
                             pack_conventions=pack_conventions)
    elif sid in BASKET_IDS:
        book, ctx = run_basket(sid, symbol, tf, segment, fee=fee, slip=slip,
                               charge_funding=charge_funding,
                               pack_conventions=pack_conventions)
    else:
        book, ctx = run_family_a(sid, symbol, tf, segment, fee=fee, slip=slip,
                                 charge_funding=charge_funding,
                                 pack_conventions=pack_conventions)
    df = load_klines(symbol, tf)
    bh = buy_and_hold_pct(df, segment)
    metrics = book_metrics(book, bh_return_pct=bh)
    metrics["strategy_id"] = sid
    metrics["symbol"] = symbol
    metrics["timeframe"] = tf
    metrics["segment"] = segment
    metrics["pack_conventions"] = pack_conventions
    # N9: the RESOLVED gate cost is measured inside the artifact (guard can
    # back it; the flat-11 constant is only a fallback)
    metrics["fee_bps_per_side"] = float(fee_bps)
    metrics["slippage_bps_per_side"] = float(slip_bps)
    metrics["cost_bp_roundtrip"] = float(rt_bps)
    metrics["cost_source"] = cost_src
    metrics["cost_symbols_resolved"] = _symbols_from_paths(paths)

    prov = {
        "adapter": "p100screen",
        "engine_version": ENGINE_VERSION,
        "fill_model": "taker_next_open",
        "signal_source": "code/prompts100/backtest100_strategies.py (verbatim)",
        "note": "the pack's signal, the repo's execution (next open, stop "
                "first, gap fills at the open, 11 bps RT per leg, funding at "
                "the real settlements); the accounting invariant is asserted "
                "inside the artifact",
    }
    return metrics, prov, []
