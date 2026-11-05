"""grid_core.py — the ATR Long Grid state machine, ONE implementation.

Why this file exists
--------------------
Today I hit the bug class where `grid_bench.py` re-implemented the grid's
state machine to get an exposure profile, and a drift assertion caught the
copy diverging from `grid_audit.py`'s simulator by 5%-963% (963% on SUI).
A second copy of a trading strategy is a second source of truth, and the two
will disagree.

So: the strategy lives here and ONLY here. `grid_audit.py` (historical
validation) and `grid_core`'s paper bot both import these functions. If the
strategy changes, both change, because there is only one thing to change.

What this module is NOT
-----------------------
It is not an exchange client and it has no opinion about fills from live data.
The paper bot drives it from real Binance CLOSED bars, so its numbers are a
forward mirror of history by construction — the same property
`paper_live.py` relies on for the CVRMD legs.

THE STRATEGY (as validated, with the four spec defects FIXED)
-------------------------------------------------------------
Long-only 5-level post-only limit grid on 15m. Each level sits one ATR(20)
below the level above, band = 5 x ATR(20) wide, so levels run from
close_prev - 1 ATR down to close_prev - 5 ATR. Each fill gets a reduce-only
cover one step above it. A close-based hard stop below the bottom level
flattens the book and starts a 96-bar cooldown. Upward drift of 1.5 x band
half flattens and re-grids higher.

Spec defects fixed here (each was verified in the audit, see STATUS.md):

  DEFECT 1 — the trend filter was not an EMA.
      It read ema[1] vs closes[1] from a 250-candle window. With the standard
      first-value seed, x[1] > E[1] <=> x[1] > x[0] because the (1-a) factor
      cancels, so the filter was "1h close > 1h close 249 bars ago" — a
      ~10.4-day momentum test. Under a NaN-until-warmed EMA it was false on
      every bar and the grid never armed at all.
      FIX: `htf_gate()` builds an EMA200 warmed over the FULL 1h history and
      compares the last COMPLETE 1h close against it. This is what the
      docstring always described.

  DEFECT 2 — the hard stop was a CLOSE stop.
      `close_now <= stop_price` means a wick through the stop that closes back
      above does nothing. That is a real and frequent outcome on 15m.
      FIX: `intrabar_stop` fires when low <= stop_price (long-only book), and
      fills at min(open, stop_price) — the conservative ordering, matching how
      the rest of this repository treats same-bar stop/target ambiguity.
      `close_only_stop=True` restores the original behaviour for comparison.

  DEFECT 3 — the trend filter never flattened an open position.
      The only bearish branch was guarded by `not pos.is_open`, so a trend
      flip left the book open until a cover or the hard stop.
      FIX: `flatten_on_bear=True` closes the book when the gate turns bearish,
      which is what "no buying into a bear trend" is supposed to mean.

  DEFECT 4 — sizing compounded off inflated equity.
      The docstring said 25% of notional per level; the code used 25% of
      EQUITY, and re-armed dead levels re-sized off current (grown) equity, so
      risk per level grew with profit.
      FIX: `size_on="notional"` (the default) sizes each level at 25% of
      CURRENT EQUITY as notional — so total notional exposure is 125% of
      equity, which is what the docstring's "about 42% margin at 3x" assumed.
      `size_on="equity"` reproduces the original buggy compounding.

Sizing invariant, asserted at construction and at every entry:
    a full 5-level grid must equal 125% of equity as NOTIONAL.
    Per-level risk is 1 ATR and total grid depth is 5 ATR, so a stop-out costs
    about (0.25 * 5 ATR) / equity per full grid.

Costs. post_only resting legs pay the MAKER fee and take no slippage; only the
market flattens (stop / rebuild / trend-loss) pay the taker fee and slippage.
Real Binance funding is charged on held notional at actual 8h events. A grid
that held 125% notional and ignored funding would be reporting a fiction.

No-lookahead contract. Every decision on bar t reads only bars <= t-1
(atr[t-1], close[t-1], and the last COMPLETE 1h bar), and an order placed on
bar t may not fill before bar t+1. This module enforces that boundary
explicitly; `paper.py` relies on it to be honest about live results.
"""
import os
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cvrmd_port as P


# --------------------------------------------------------------------------
# Strategy parameters. Defaults are the FIXED spec; every original value is
# kept as a named constant so the "before" behaviour stays reproducible.
# --------------------------------------------------------------------------
GRID_LEVELS = 5
ATR_PERIOD = 20
ATR_BAND_MULT = 5.0
HTF_EMA_PERIOD = 200
HTF_MIN_CANDLES = 400          # spec asked for 250; a 200-EMA needs >200+warmup
EQUITY_PCT_PER_LEVEL = 0.25
LEVERAGE = 3.0
MAINTENANCE_MARGIN = 0.005
STOP_ATR_MULT = 0.5
COOLDOWN_BARS = 96
REBUILD_DRIFT_MULT = 1.5
WARMUP_BARS = 28

MAKER_FEE = 0.0002              # Hyperliquid: 0.02% maker
TAKER_FEE = 0.0005              #              0.05% taker
MAKER_SLIP = 0.0                # a resting post-only order earns the touch
TAKER_SLIP = 0.0005
HOUSE_COMM = 0.0006
HOUSE_SLIP = 0.0005

# original, unfixed spec values, for A/B comparison
ORIG = dict(htf_limit=250, close_only_stop=True, flatten_on_bear=False,
            size_on="equity")

INITIAL_EQUITY = 10000.0


# --------------------------------------------------------------------------
# indicators
# --------------------------------------------------------------------------
def shift(x, k):
    """Pine ta.shift / series[k]: NaN-padded forward shift."""
    out = np.full(len(x), np.nan)
    if k >= 0 and k < len(x):
        out[k:] = x[:len(x) - k]
    return out


def atr(h, l, c, n=ATR_PERIOD):
    return P.atr(h, l, c, n)


def htf_gate(bars_1h, period=HTF_EMA_PERIOD, min_candles=HTF_MIN_CANDLES):
    """DEFECT 1 FIX. One boolean per 1h bar: close > warmed EMA(period).

    `bars_1h` must be ordered oldest-first. Returns False until there are at
    least `min_candles` bars, so the EMA is genuinely warmed rather than
    seeded from a single value — the mistake that made the original filter
    collapse to a 249-bar momentum test.
    """
    if len(bars_1h) < min_candles:
        return np.zeros(len(bars_1h), bool), np.full(len(bars_1h), np.nan)
    c = np.array([b[4] for b in bars_1h], float)
    e = P.ema(c, period)
    return c > e, e


def htf_gate_broken(bars_1h, limit=ORIG["htf_limit"]):
    """The ORIGINAL, UNFIXED filter, kept so the fix can be A/B measured.

    Reads ema[1] against closes[1] of a sliding `limit`-candle window, which
    with a first-value EMA seed is identically "close 1 bar ago > close
    `limit` bars ago". Under a NaN-until-warmed EMA it is always False.
    """
    c = np.array([b[4] for b in bars_1h], float)
    n = len(c)
    win = min(limit, n)
    gate = np.zeros(n, bool)
    if win < 2:
        return gate
    # A full `win`-candle window must exist, i.e. bar i needs c[i-win .. i-1].
    # grid_audit.py gates on idx >= win-1; matching that exactly is what makes
    # the parity test compare the strategy instead of two different filters.
    ok = np.zeros(n, bool)
    ok[win - 1:] = c[win - 2:n - 1] > c[0:n - win + 1]
    return ok


# --------------------------------------------------------------------------
# the strategy
# --------------------------------------------------------------------------
class GridState:
    """Container for the engine's own state, so a caller can inspect or
    serialise it (the paper bot snapshots this every cycle)."""

    def __init__(self):
        self.state = "idle"
        self.cash = INITIAL_EQUITY
        self.lots = []            # [qty, fill_px, level, fees_paid]
        self.grid_px = [0.0] * GRID_LEVELS
        self.grid_qty = [0.0] * GRID_LEVELS
        self.ent_live = [None] * GRID_LEVELS
        self.cov_live = [None] * GRID_LEVELS
        self.step = 0.0
        self.stop_px = 0.0
        self.center = 0.0
        self.half = 0.0
        self.cooldown_left = 0
        self.bars_since = 0
        self.last_ts = 0

    def snapshot(self, price):
        inv = sum(l[0] * price for l in self.lots)
        return dict(
            state=self.state,
            equity=self.cash + inv,
            cash=self.cash,
            notional=inv,
            open_levels=[l[2] for l in self.lots],
            open_qty=sum(l[0] for l in self.lots),
            avg_entry=(sum(l[0] * l[1] for l in self.lots)
                       / sum(l[0] for l in self.lots)) if self.lots else 0.0,
            exposure=(inv / (self.cash + inv)) if (self.cash + inv) > 0 else 0.0,
            grid_px=list(self.grid_px),
            grid_qty=list(self.grid_qty),
            step=self.step,
            stop_px=self.stop_px,
            center=self.center,
            cooldown_left=self.cooldown_left,
            last_ts=self.last_ts,
        )


class GridEngine:
    """The strategy. Feed it closed 15m bars plus the 1h gate; it advances
    one bar and appends any log events.

    Logs are tuples `(bar_ts, kind, detail)` where kind is one of
    grid_built, entry_fill, cover_fill, stop, rebuild, stand_down,
    liquidation.
    """

    def __init__(self, levels=GRID_LEVELS, atr_period=ATR_PERIOD,
                 atr_mult=ATR_BAND_MULT, equity_pct=EQUITY_PCT_PER_LEVEL,
                 stop_atr=STOP_ATR_MULT, cooldown=COOLDOWN_BARS,
                 drift=REBUILD_DRIFT_MULT, warmup=WARMUP_BARS,
                 maker_fee=MAKER_FEE, taker_fee=TAKER_FEE,
                 maker_slip=MAKER_SLIP, taker_slip=TAKER_SLIP,
                 close_only_stop=ORIG["close_only_stop"],
                 flatten_on_bear=ORIG["flatten_on_bear"],
                 size_on=ORIG["size_on"],
                 initial_equity=INITIAL_EQUITY,
                 funding=None, bar_index=None):
        self.p = dict(levels=levels, atr_period=atr_period, atr_mult=atr_mult,
                      equity_pct=equity_pct, stop_atr=stop_atr,
                      cooldown=cooldown, drift=drift, warmup=warmup,
                      maker_fee=maker_fee, taker_fee=taker_fee,
                      maker_slip=maker_slip, taker_slip=taker_slip,
                      close_only_stop=close_only_stop,
                      flatten_on_bear=flatten_on_bear, size_on=size_on,
                      initial_equity=initial_equity)
        # funding: optional (rate_array, is_event_array) aligned to the bar
        # index, supplied by the caller so this module never touches the
        # network. `bar_index` is the function through which the current bar
        # looks itself up, because the arrays are per-bar.
        self.funding = funding
        self.bar_index = bar_index if bar_index is not None else (lambda i: (0.0, False))
        self.st = GridState()
        self._bar_i = 0
        # per-level grid sizing is rebuilt with the grid, so it lives here
        self._grid_px = [0.0] * levels
        self._grid_qty = [0.0] * levels
        self._ent = [None] * levels
        self._cov = [None] * levels
        self._cov_bar = [-1] * levels    # bar a cover was PLACED, for the
                                         # next-bar-eligibility rule
        self.counts = defaultdict(int)
        self.pnl_log = []

    # -- sizing invariant -------------------------------------------------
    def _level_qty(self, level_px, equity):
        """qty for one level.

        size_on='notional' (FIXED): each level is `equity_pct` of CURRENT
        EQUITY expressed as notional, so a full grid is 125% of equity.
        size_on='equity' (ORIGINAL): 25% of equity as a MARGIN commitment,
        which the audit showed compounds risk with profits.
        """
        e = max(equity, 0.0)
        if self.p["size_on"] == "notional":
            target_notional = self.p["equity_pct"] * e
            return target_notional / level_px
        return self.p["equity_pct"] * e / level_px

    def grid_notional(self, equity):
        """Notional a full, fully-filled grid would carry at `equity`.

        The docstring's invariant is that this equals 125% of equity, which is
        where its "about 42% margin at 3x" figure came from. The original code
        did not satisfy it, because a re-armed level re-sized off grown equity.
        """
        if not any(self._grid_px):
            return 0.0
        return sum(self._level_qty(px, equity) * px for px in self._grid_px)

    # -- helpers ----------------------------------------------------------
    def qty(self):
        return sum(l[0] for l in self.st.lots)

    def equity(self, px):
        # Equity = cash + position MARKET VALUE. The audit's expensive bug was
        # computing this as cash + unrealised, which omits the cost basis and
        # drives equity negative on a perfectly healthy leveraged book.
        return self.st.cash + sum(l[0] * px for l in self.st.lots)

    def _close(self, amount, px, fee, slip, kind, bar_ts, reason):
        """Sell `amount` at `px`. Returns realised P&L for the slice."""
        st = self.st
        cash = st.cash
        realised = 0.0
        remaining = amount
        for lot in list(st.lots):
            if remaining <= 1e-12:
                break
            take = min(lot[0], remaining)
            fill_px = px * (1 - slip)
            cash += take * fill_px
            f = take * fill_px * fee
            cash -= f
            realised += take * (fill_px - lot[1]) - lot[3] - f
            lot[3] += f
            lot[0] -= take
            if lot[0] <= 1e-12:
                st.lots.remove(lot)
            remaining -= take
        st.cash = cash
        if abs(realised) > 1e-12:
            self.pnl_log.append((bar_ts, kind, reason, realised))
        return realised

    def _clear_grid(self):
        self._grid_px = [0.0] * self.p["levels"]
        self._grid_qty = [0.0] * self.p["levels"]
        self._ent = [None] * self.p["levels"]
        self._cov = [None] * self.p["levels"]
        st = self.st
        st.step = st.stop_px = st.center = st.half = 0.0

    # -- one bar ----------------------------------------------------------
    def step_bar(self, t, o, h, l, c, v, gate_now, atr_prev, close_prev,
                 bar_i=None):
        """Advance one CLOSED 15m bar.

        `gate_now`  bool, the trend filter for this bar (from the last
                    COMPLETE 1h bar — never the forming one).
        `atr_prev`  the PREVIOUS 15m bar's ATR, per the spec's atr[1].
        `close_prev`  the PREVIOUS 15m bar's close, per the spec's
                     candles.closes[1]. The grid is built from it, so it is an
                     explicit argument rather than a side channel that can
                     silently hold a stale value.
        """
        st = self.st
        st.bars_since += 1
        st.last_ts = t
        if bar_i is not None:
            self._bar_i = bar_i
        st.last_price = c
        logs = []

        # -- cooldown --
        if st.state == "cooldown":
            st.cooldown_left -= 1
            if st.cooldown_left <= 0:
                st.state = "idle"
            return logs

        # -- warmup --
        if st.bars_since < self.p["warmup"]:
            return logs

        if atr_prev is None or (isinstance(atr_prev, float) and np.isnan(atr_prev)) \
                or atr_prev <= 0:
            return logs

        nlev = self.p["levels"]
        bull = bool(gate_now)

        # ================= IDLE: build the grid =================
        if st.state == "idle":
            if not bull:
                return logs
            half = atr_prev * self.p["atr_mult"]
            step = half / nlev
            equity = self.equity(close_prev)
            self._grid_px = [close_prev - step * (i + 1) for i in range(nlev)]
            self._grid_qty = [self._level_qty(p, equity) for p in self._grid_px]
            st.center = close_prev
            st.stop_px = self._grid_px[-1] - atr_prev * self.p["stop_atr"]
            st.state = "working"
            self.counts["grid_built"] += 1
            logs.append((t, "grid_built", dict(center=close_prev, step=step,
                                              stop=st.stop_px,
                                              levels=list(self._grid_px))))
            # resting orders may not fill on the bar they are placed
            for i in range(nlev):
                if self._grid_px[i] < c:
                    self._ent[i] = self._grid_px[i]
            return logs

        # ================= WORKING =================
        # 1. resting entry limits fill (never on the bar they were placed)
        for i in range(nlev):
            if self._ent[i] is None:
                continue
            p = self._ent[i]
            if l <= p:
                q = self._grid_qty[i]
                px = p * (1 + self.p["maker_slip"])
                f = q * px * self.p["maker_fee"]
                st.cash -= q * px + f
                st.lots.append([q, px, i, f])
                self._ent[i] = None
                self._cov[i] = p + st.step
                self._cov_bar[i] = t
                self.counts["entry_fill"] += 1
                logs.append((t, "entry_fill", dict(level=i, qty=q, price=px)))

        # 2. reduce-only covers fill.
        # A cover is only eligible from the BAR AFTER it was placed. Without
        # this, a level that just filled at p has its cover at p+step checked
        # against the same bar's high -- and since the low touched p, the high
        # is nearly always above p+step, so every entry self-closes on its own
        # fill bar for two fees and one spread. That produced 126,628
        # round trips in the parity run versus 5,233 in the audit.
        for i in range(nlev):
            if self._cov[i] is None:
                continue
            if self._cov_bar[i] == t:
                continue          # placed this bar, not yet eligible
            p = self._cov[i]
            if h >= p:
                realised = self._close(self._grid_qty[i], p,
                                       self.p["maker_fee"], self.p["maker_slip"],
                                       "cover", t, f"level{i}")
                self.counts["cover_fill"] += 1
                logs.append((t, "cover_fill", dict(level=i, price=p,
                                                   pnl=round(realised, 4))))
                self._cov[i] = None
                self._cov_bar[i] = -1

        # 3. hard stop — DEFECT 2 FIX (intrabar by default)
        stopped = False
        if self.p["close_only_stop"]:
            stopped = c <= st.stop_px
        else:
            stopped = l <= st.stop_px
        if stopped:
            if st.lots:
                fill_px = min(o, st.stop_px) if l <= st.stop_px else c
                self._close(self.qty(), fill_px, self.p["taker_fee"],
                            self.p["taker_slip"], "stop", t, "hard_stop")
            self.counts["stop"] += 1
            logs.append((t, "stop", dict(price=st.stop_px, close=c)))
            self._clear_grid()
            st.state = "cooldown"
            st.cooldown_left = self.p["cooldown"]
        else:
            # 4. re-arm dead levels while the filter holds
            for i in range(nlev):
                if self._ent[i] is None and self._cov[i] is None:
                    if bull and self._grid_px[i] < c:
                        self._ent[i] = self._grid_px[i]
            # 5. rebuild on upward drift
            if c > st.center + st.half * self.p["drift"]:
                if st.lots:
                    self._close(self.qty(), c * (1 - self.p["taker_slip"]),
                                self.p["taker_fee"], 0.0, "rebuild", t,
                                "drift_rebuild")
                self.counts["rebuild"] += 1
                logs.append((t, "rebuild", dict(close=c)))
                self._clear_grid()
                st.state = "idle"
            elif (not bull) and self.p["flatten_on_bear"] and st.lots:
                # DEFECT 3 FIX: a trend flip closes the book
                self._close(self.qty(), c * (1 - self.p["taker_slip"]),
                            self.p["taker_fee"], 0.0, "bear_flatten", t,
                            "trend_bearish")
                self.counts["bear_flatten"] += 1
                logs.append((t, "bear_flatten", dict(close=c)))
                self._clear_grid()
                st.state = "idle"
            elif (not bull) and not st.lots:
                # original behaviour: stand down while flat
                self.counts["stand_down"] += 1
                st.state = "idle"
                self._clear_grid()

        # 6. funding on held notional at real 8h events
        if self.funding is not None and st.lots:
            rate, is_ev = self.bar_index(self._bar_i)
            if is_ev:
                st.cash -= self.qty() * c * rate
        return logs

# --------------------------------------------------------------------------
# a plain-function runner for validation, built on the SAME engine class, so
# validation and paper can never drift apart.
# --------------------------------------------------------------------------
def run(bars_15m, gate_15m, funding_arrays=None, atr_series=None,
        **engine_kw):
    """Run the engine over `bars_15m`, returning a stats dict.

    `gate_15m`  bool array, one per 15m bar, built from 1h CLOSED bars.
    `funding_arrays` (rate, is_event) arrays aligned to bars_15m, or None.
    """
    n = len(bars_15m)
    if atr_series is None:
        h = np.array([b[2] for b in bars_15m], float)
        l = np.array([b[3] for b in bars_15m], float)
        c = np.array([b[4] for b in bars_15m], float)
        atr_series = atr(h, l, c, engine_kw.get("atr_period", ATR_PERIOD))
    eng = GridEngine(funding=funding_arrays, **engine_kw)
    if funding_arrays is not None:
        _fr, _fe = funding_arrays
        eng.bar_index = lambda i: (float(_fr[i]), bool(_fe[i]))
    logs = []
    eq_curve = np.zeros(n)
    expo_curve = np.zeros(n)
    for t in range(n):
        prev_close = bars_15m[t - 1][4] if t >= 1 else None
        atr_prev = atr_series[t - 1] if t >= 1 else None
        logs.extend(eng.step_bar(bars_15m[t][0], bars_15m[t][1], bars_15m[t][2],
                                 bars_15m[t][3], bars_15m[t][4], bars_15m[t][5],
                                 gate_15m[t], atr_prev, prev_close, bar_i=t))
        eq_curve[t] = eng.equity(bars_15m[t][4])
        expo_curve[t] = (eng.qty() * bars_15m[t][4] / max(eq_curve[t], 1e-9))

    st = eng.st
    eq = eng.equity(bars_15m[-1][4])
    peak = np.maximum.accumulate(eq_curve)
    mdd = float(np.max((peak - eq_curve) / np.maximum(peak, 1e-9)))
    return dict(
        engine=eng, logs=logs, eq_curve=eq_curve, expo_curve=expo_curve,
        equity=eq, mdd=mdd * 100, counts=dict(eng.counts),
        pnl_log=list(eng.pnl_log), state=st,
    )