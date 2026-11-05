#!/usr/bin/env python3
"""
xrp_live_bot.py — LIVE / TESTNET executor for the NEUTRAL XRP book (v2 sizing).

WHAT THIS IS
------------
The order-placement layer UNDER the validated paper mirror. The brain stays
exactly where it has always been: code/xrp_neutral_engine.py, byte-locked,
re-run over the full history every cycle — the same "no second fill simulator"
discipline as the paper bot. This file does not decide anything the engine has
not already decided. Each cycle it:

  1. pulls closed bars + the FULL funding history (same code as the paper bot,
     imported from it, pointed at this bot's own data directory);
  2. runs the engine and reads the DESIRED book state (open lots, resting
     rungs, state machine, stop geometry) through a state-exposing variant of
     the engine that is built IN MEMORY by applying ONE exactly-matched literal
     patch to the audited source — the file on disk is never modified, its
     sha256 is asserted against the hash the verified artifact pins, and the
     patched variant must reproduce the locked engine's numbers bit-for-bit
     (parity check) before the bot ever places an order;
  3. diffs the desired book against the ACTUAL exchange book (hedge-mode
     positions + open orders) and trades the diff:
       * rungs        -> post-only LIMIT orders (GTX) at the engine's prices,
                         LONG side bids below / SHORT side asks above;
       * open covers  -> reduce-side LIMIT orders at each lot's cover price;
       * stop/trend flatten, refused-fill excess, missed fills -> MARKET orders
         that force the exchange book back onto the engine book;
  4. writes xrp_live_bot_recon.jsonl — per NEW 15m bar, engine-modeled fills vs
     actual exchange fills, side by side. This is the LIVE analog of
     funding_covers_bars: a live book whose fills the exchange does not confirm
     is a different book, and the divergence is measured, never asserted;
  5. writes xrp_live_bot_status.json and a bt-artifact/1 artifact, so the same
     guard/verify discipline as every campaign in this repo applies.

STAGES (do not skip)
--------------------
    paper (running on the VPS)  ->  testnet  ->  live at day-0 scale  ->  scale
The bot refuses to place REAL orders unless an ARMED file exists in its
directory, and that file is only created by `--arm-live`, which demands a typed
confirmation. Testnet needs no arming (fake money).

SAFETY RULES ENFORCED HERE (all hard, all measured)
---------------------------------------------------
  * engine sha256 must equal ENGINE_SHA (the hash the verified artifact
    fe5c359a22c8dffe pins). A moved engine = no trading.
  * funding_covers_bars must be TRUE or NOTHING is placed (partially-funded
    equity is wrong equity, and sizing derives from equity).
  * parity patched-vs-locked engine must hold or NOTHING is placed.
  * XRPUSDT only. Orders per cycle capped. No reduceOnly in hedge mode (the
    positionSide IS the reduce direction). Client order ids are deterministic,
    so a retried cycle cannot double-place.
  * the kill rule travels with the book: engine forward PF < 1.0 on >= 30
    closed lots = KILL (same as the paper bot), plus a LIVE-only kill: the
    recon fill-match rate below RECON_KILL_MATCH_PCT over the recent window.

RUNNING
-------
    python xrp_live_bot.py --init  --net testnet   # exchange setup + parity + day-0
    python xrp_live_bot.py --once  --net testnet   # one cron cycle
    python xrp_live_bot.py --arm-live              # interactive; writes ARMED
    python xrp_live_bot.py --status | --recon | --snapshot
    cron: 1-56/5 * * * *  /home/ubuntu/xrp-live-bot/run.sh

Keys come from the environment (BINANCE_TESTNET_KEY / BINANCE_TESTNET_SECRET,
BINANCE_LIVE_KEY / BINANCE_LIVE_SECRET), sourced by run.sh from a root-only
.env. The key must have futures enabled, withdrawals DISABLED, and be
IP-whitelisted to the VPS.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import types
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

# The data helpers (kline pull, funding pull, coverage check) are IMPORTED from
# the paper bot, not copied: two copies of the data pipeline is exactly the
# drift class that burned this repo before. Importing it also sets
# X.EQUITY_PCT to the paper bot's value; we set our own overlay right after.
import xrp_paper_bot as PAPER          # noqa: E402
import xrp_neutral_engine as X         # noqa: E402

# ── the locked engine: hash the verified artifact pins ─────────────────────
# results/runs/fe5c359a22c8dffe.json -> core.engine_sha256. If code/
# xrp_neutral_engine.py ever stops matching this, the bot trades NOTHING: every
# number this book was validated with was produced by those bytes.
ENGINE_SHA = "e6f7422f53d30d8718d6ad3d337d0dca8e342512390be7f75b009ed2df3d636f"

SYMBOL = "XRPUSDT"
INTERVAL = "15m"
TF_MS = 15 * 60 * 1000

NETS = {
    "testnet": "https://testnet.binancefuture.com",
    "live": "https://fapi.binance.com",
}

# ── sizing: v2, byte-for-byte the paper bot's declared cell ─────────────────
# (xrp_paper_bot.py CONFIG comment: choosing different values here would be a
# new search on top of a new sizing, with no multiple-testing story. Same rule.)
INIT_USDT = 25.0
EQUITY_PCT = 1.0
LEVERAGE = 10.0
MAINT_MARGIN = 0.005
DELTA_MAX_PCT = 2.0
CONFIG = dict(trend_band=0.10, stop_atr_mult=0.5, cover_mult=1.0)
X.EQUITY_PCT = EQUITY_PCT          # after the paper-bot import, explicitly ours

# exchange filters (asserted against exchangeInfo at --init; refreshed lazily)
STEP_SIZE = 0.1                    # XRPUSDT LOT_SIZE stepSize
TICK_SIZE = 0.0001                 # XRPUSDT PRICE_FILTER tickSize
MIN_NOTIONAL = 5.0                 # XRPUSDT MIN_NOTIONAL notional

MAX_ORDERS_PER_CYCLE = 40
POSITION_TOL_QTY = STEP_SIZE       # one lot-step of position drift is tolerated
RECON_KILL_MATCH_PCT = 80.0        # < this over the recent window = live kill
RECON_WINDOW = 100                 # engine events considered for the kill check

HOME = os.environ.get("XRP_BOT_HOME") or HERE
STATUS = os.path.join(HOME, "xrp_live_bot_status.json")
DAY0 = os.path.join(HOME, "xrp_live_bot_day0.json")
RECON = os.path.join(HOME, "xrp_live_bot_recon.jsonl")
STATE = os.path.join(HOME, "xrp_live_bot_state.json")      # prev cycle book
PARITY = os.path.join(HOME, "xrp_live_bot_parity.json")
ARTDIR = os.path.join(HOME, "artifacts")
ARMED = os.path.join(HOME, "ARMED")


def fail(msg):
    print(f"FATAL: {msg}", flush=True)
    sys.exit(1)


# ── the state-exposing engine variant (built in memory, never on disk) ──────
# The audited simulate() reports closed trades and curves through `track`, but
# the OPEN book (lots, resting rungs, state machine, stop geometry) lives in
# loop locals. Reading it requires either a second simulator (forbidden: two
# engines disagreeing is the drift class that produced grid_core's 11,966
# fills vs the validator's 5,233) or an exactly-matched literal patch of the
# audited source, exec'd in memory — the same technique as
# code/_build_funding_engine.py. The disk file is never touched; the sha is
# asserted; and parity (identical closed-trade stream) is enforced.
_TRACK_PATCH_FROM = "n_funding_events=n_fund, init=init))"
_TRACK_PATCH_TO = (
    "n_funding_events=n_fund, init=init,\n"
    "            open_book=dict(state=state, cooldown_left=cooldown_left,\n"
    "                           center=center, half=half, step=step,\n"
    "                           lots=[[l_[0], l_[1], l_[2], l_[3]] for l_ in lots],\n"
    "                           orders=[[o_[0], o_[1], o_[2]] for o_ in orders],\n"
    "                           last_bar_index=t)))"
)


def build_state_engine():
    """Returns the engine module exposing simulate() plus open_book in track."""
    path = os.path.join(HERE, "xrp_neutral_engine.py")
    raw = open(path, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != ENGINE_SHA:
        fail(f"xrp_neutral_engine.py sha {sha[:16]} != pinned {ENGINE_SHA[:16]} "
             f"- the engine moved; re-validate before trading anything")
    crlf = b"\r\n" in raw
    src = raw.decode("utf-8").replace("\r\n", "\n")
    cnt = src.count(_TRACK_PATCH_FROM)
    if cnt != 1:
        fail(f"state patch matches {cnt} times in the engine source "
             f"(must be exactly 1) - refusing to guess")
    patched = src.replace(_TRACK_PATCH_FROM, _TRACK_PATCH_TO)
    if crlf:
        patched = patched.replace("\n", "\r\n")
    mod = types.ModuleType("xrp_neutral_engine_live_state")
    mod.__file__ = path
    code = compile(patched, "<xrp_neutral_engine_live_state>", "exec")
    exec(code, mod.__dict__)
    # the exec'd source carries the ENGINE'S default EQUITY_PCT (0.25); the
    # locked module carries the bot's overlay (1.0, set below at import).
    # Sizing is a module global read inside ladder(), so the overlay MUST be
    # mirrored or the patched book trades quarter-size lots. The parity check
    # catches exactly this class of bug; mirror it here so parity passes.
    mod.EQUITY_PCT = X.EQUITY_PCT
    return mod


def parity_check(state_engine, fund_dir):
    """The patched engine must reproduce the locked engine EXACTLY. Runs both
    over the real history and compares the closed-trade stream field by
    field. Writes PARITY on success; the file carries the engine sha, so an
    engine move invalidates it automatically."""
    bars = PAPER.load_bars(PAPER.csv_path(SYMBOL))
    if len(bars) < 2000:
        fail(f"parity needs the bar history ({len(bars)} bars present)")
    t1, t2 = {}, {}
    eq1 = X.simulate(bars, SYMBOL, funding=True, fund_dir=fund_dir,
                     init=INIT_USDT, delta_max_pct=DELTA_MAX_PCT, track=t1,
                     **CONFIG)
    eq2 = state_engine.simulate(bars, SYMBOL, funding=True, fund_dir=fund_dir,
                                init=INIT_USDT, delta_max_pct=DELTA_MAX_PCT,
                                track=t2, **CONFIG)
    diffs = []
    if eq1 != eq2:
        diffs.append(f"eq {eq1!r} != {eq2!r}")
    for k in ("fills", "cycles", "grids", "open_lots", "delta_cap_hits",
              "stand_down_bars", "n_funding_events"):
        if t1[k] != t2[k]:
            diffs.append(f"{k}: {t1[k]} != {t2[k]}")
    if t1["closed_pnl"] != t2["closed_pnl"]:
        diffs.append("closed_pnl streams differ")
    if t1["fees"] != t2["fees"] or t1["fund"] != t2["fund"]:
        diffs.append("fees/funding differ")
    ob = t2["open_book"]
    for k in ("state", "cooldown_left", "center", "half", "step", "lots",
              "orders", "last_bar_index"):
        if k not in ob:
            diffs.append(f"open_book missing {k}")
    if diffs:
        fail("parity patched-vs-locked FAILED: " + "; ".join(diffs))
    cur_sha = hashlib.sha256(
        open(os.path.join(HERE, "xrp_neutral_engine.py"), "rb").read()).hexdigest()
    json.dump({"engine_sha256": cur_sha,
               "checked_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "bars": len(bars), "eq": eq1, "fills": t1["fills"],
               "open_book_keys": sorted(ob.keys())},
              open(PARITY, "w"), indent=1)
    print(f"parity OK: patched engine reproduces the locked engine exactly "
          f"({len(bars):,} bars, {t1['fills']} fills)", flush=True)


def state_engine_fresh():
    """PARITY exists and was written against the CURRENT engine bytes."""
    if not os.path.exists(PARITY):
        return False
    try:
        p = json.load(open(PARITY))
    except Exception:
        return False
    cur = hashlib.sha256(open(os.path.join(HERE, "xrp_neutral_engine.py"),
                              "rb").read()).hexdigest()
    return p.get("engine_sha256") == cur == ENGINE_SHA


# ── signed REST ─────────────────────────────────────────────────────────────
class RestError(Exception):
    def __init__(self, status, body):
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}: {body[:200]}")


class Exchange:
    def __init__(self, net):
        if net not in NETS:
            fail(f"unknown net {net!r}")
        self.net = net
        self.base = NETS[net]
        self.key = os.environ.get(f"BINANCE_{net.upper()}_KEY", "")
        self.secret = os.environ.get(f"BINANCE_{net.upper()}_SECRET", "")
        self.time_off_ms = 0
        if not self.key or not self.secret:
            fail(f"missing BINANCE_{net.upper()}_KEY / _SECRET in the environment")

    # -- low level -----------------------------------------------------------
    def _req(self, method, path, params, signed=False, tries=3):
        params = dict(params or {})
        headers = {"User-Agent": "xrp-live-bot/1.0"}
        if signed:
            params["recvWindow"] = 10000
            params["timestamp"] = int(time.time() * 1000) + self.time_off_ms
            qs = urllib.parse.urlencode(params)
            sig = hmac.new(self.secret.encode(), qs.encode(),
                           hashlib.sha256).hexdigest()
            url = f"{self.base}{path}?{qs}&signature={sig}"
            headers["X-MBX-APIKEY"] = self.key
        else:
            url = f"{self.base}{path}" + (f"?{urllib.parse.urlencode(params)}"
                                          if params else "")
        last = None
        for attempt in range(tries):
            try:
                req = urllib.request.Request(url, headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=20) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")
                # a business error is final: retrying it would be a bug
                raise RestError(e.code, body)
            except Exception as e:            # transport: retry with backoff
                last = e
                if attempt < tries - 1:
                    time.sleep(1.5 * (attempt + 1))
        raise last

    # -- public --------------------------------------------------------------
    def time_offset(self):
        st = int(time.time() * 1000)
        srv = self._req("GET", "/fapi/v1/time", {})["serverTime"]
        self.time_off_ms = srv - st
        return self.time_off_ms

    def exchange_info(self):
        return self._req("GET", "/fapi/v1/exchangeInfo", {})

    # -- signed reads --------------------------------------------------------
    def account(self):
        return self._req("GET", "/fapi/v2/account", {}, signed=True)

    def positions(self):
        rows = self._req("GET", "/fapi/v2/positionRisk",
                         {"symbol": SYMBOL}, signed=True)
        return {r["positionSide"]: r for r in rows
                if r.get("symbol") == SYMBOL}

    def open_orders(self):
        return self._req("GET", "/fapi/v1/openOrders",
                         {"symbol": SYMBOL}, signed=True)

    def user_trades(self, from_id=None):
        params = {"symbol": SYMBOL, "limit": 1000}
        if from_id:
            params["fromId"] = int(from_id)
        return self._req("GET", "/fapi/v1/userTrades", params, signed=True)

    def funding_income(self, since_ms):
        out, st = [], since_ms
        while True:
            page = self._req("GET", "/fapi/v1/income",
                             {"symbol": SYMBOL, "incomeType": "FUNDING_FEE",
                              "startTime": st, "limit": 1000}, signed=True)
            out.extend(page)
            if len(page) < 1000:
                return out
            st = int(page[-1]["time"]) + 1
            time.sleep(0.15)

    def commission_rate(self):
        return self._req("GET", "/fapi/v1/commissionRate",
                         {"symbol": SYMBOL}, signed=True)

    # -- signed writes -------------------------------------------------------
    def setup(self):
        """Idempotent account preparation: dual-side positions, 10x, isolated."""
        dual = self._req("GET", "/fapi/v1/positionSide/dual", {}, signed=True)
        if not dual.get("dualSidePosition"):
            self._req("POST", "/fapi/v1/positionSide/dual",
                      {"dualSidePosition": "true"}, signed=True)
            print("  position mode -> HEDGE (dual-side)", flush=True)
        self._req("POST", "/fapi/v1/leverage",
                  {"symbol": SYMBOL, "leverage": int(LEVERAGE)}, signed=True)
        try:
            self._req("POST", "/fapi/v1/marginType",
                      {"symbol": SYMBOL, "marginType": "ISOLATED"}, signed=True)
        except RestError as e:
            if "-4046" not in e.body:      # -4046: no need to change margin type
                raise
        cr = self.commission_rate()
        print(f"  setup ok (net={self.net}, leverage {LEVERAGE}x, isolated, "
              f"maker {cr.get('makerCommissionRate')}, "
              f"taker {cr.get('takerCommissionRate')})", flush=True)

    def place_limit(self, side, position_side, qty, price, client_id, post_only=True):
        p = {"symbol": SYMBOL, "side": side, "positionSide": position_side,
             "type": "LIMIT", "timeInForce": "GTX" if post_only else "GTC",
             "quantity": qty, "price": price, "newClientOrderId": client_id}
        return self._req("POST", "/fapi/v1/order", p, signed=True)

    def place_market(self, side, position_side, qty, client_id):
        # hedge mode: side+positionSide IS the reduce direction; reduceOnly is
        # not a valid parameter here (-1106 if sent)
        p = {"symbol": SYMBOL, "side": side, "positionSide": position_side,
             "type": "MARKET", "quantity": qty, "newClientOrderId": client_id}
        return self._req("POST", "/fapi/v1/order", p, signed=True)

    def cancel(self, order_id):
        return self._req("DELETE", "/fapi/v1/order",
                         {"symbol": SYMBOL, "orderId": order_id}, signed=True)

    def cancel_all(self):
        return self._req("DELETE", "/fapi/v1/allOpenOrders",
                         {"symbol": SYMBOL}, signed=True)


# ── exchange-side formatting ────────────────────────────────────────────────
def fmt_qty(q):
    q = float(np.floor(q / STEP_SIZE) * STEP_SIZE)
    return f"{q:.1f}"


def fmt_px(p):
    p = round(p / TICK_SIZE) * TICK_SIZE
    return f"{p:.4f}"


def round_qty(q):
    return float(np.floor(q / STEP_SIZE) * STEP_SIZE)


# ── the desired book, in exchange terms ─────────────────────────────────────
def desired_orders(open_book, scale):
    """(rungs, covers) the engine book implies as RESTING exchange orders.

    scale maps engine-USDT to the day-0 account: the engine replays 2020+ and
    COMPOUNDS (terminal equity in the millions), while the live account holds
    INIT_USDT. The engine is exactly linear in equity (sizing, fees, funding
    and the delta-cap ratio all scale), so every QUANTITY is engine qty * scale
    — the same normalisation the paper bot applies to its USDT reporting.

    rungs exist only while the engine state is 'working': 'idle' means the
    ladder re-arms at the NEXT close (the engine has not chosen a centre yet),
    'cooldown' means 96 bars of nothing. Covers exist for every open lot, on
    the reduce side of its own position (hedge mode closes by side).
    """
    rungs, covers = [], []
    if open_book["state"] == "working":
        for px, side, q in open_book["orders"]:
            rungs.append(dict(side="BUY" if side > 0 else "SELL",
                              position_side="LONG" if side > 0 else "SHORT",
                              qty=fmt_qty(q * scale), price=fmt_px(px),
                              kind="rung", engine_px=float(px),
                              engine_qty=float(q)))
    for qty_s, fill_px, cover_px, _fee in open_book["lots"]:
        covers.append(dict(side="SELL" if qty_s > 0 else "BUY",
                           position_side="LONG" if qty_s > 0 else "SHORT",
                           qty=fmt_qty(abs(qty_s) * scale),
                           price=fmt_px(cover_px), kind="cover",
                           engine_px=float(cover_px),
                           engine_qty=abs(float(qty_s))))
    return rungs, covers


def desired_positions(open_book, scale):
    """{LONG: qty, SHORT: qty} the engine book implies, at ACCOUNT scale."""
    long_q = sum(l[0] for l in open_book["lots"] if l[0] > 0)
    short_q = -sum(l[0] for l in open_book["lots"] if l[0] < 0)
    return {"LONG": round_qty(long_q * scale), "SHORT": round_qty(short_q * scale)}


def cid(bar_index, kind, k=0):
    # deterministic <= 36 chars: a retried cycle re-derives the same ids and
    # finds them already resting instead of double-placing
    return f"xlv{bar_index % 10**10}-{kind}{k}"


# ── the cycle ───────────────────────────────────────────────────────────────
def cycle(net, ex):
    os.makedirs(HOME, exist_ok=True)
    os.makedirs(ARTDIR, exist_ok=True)

    if not state_engine_fresh():
        fail("parity file missing or stale for the current engine bytes - "
             "run --init (parity is a precondition for trading)")
    if net == "live" and not os.path.exists(ARMED):
        fail("live net requires the ARMED file (see --arm-live)")

    # 1. data: same helpers as the paper bot, pointed at THIS bot's data dir
    path, n_new, note = PAPER.pull_klines(SYMBOL, INTERVAL, TF_MS)
    if note != "ok":
        print(f"  kline pull failed: {note}")
        return
    n_fund, note_f = PAPER.pull_funding(SYMBOL, PAPER.FUNDING_FLOOR_MS)
    if note_f != "ok":
        print(f"  funding pull failed: {note_f}")
    bars = PAPER.load_bars(path)
    if len(bars) < 2000:
        print(f"  only {len(bars)} bars, not enough to run")
        return
    covers_bars, f_first, f_last, f_n = PAPER.funding_coverage(bars, PAPER.FUNDDIR)
    if not covers_bars:
        # partially-funded equity is wrong equity, and sizing derives from it
        fail("funding history does not cover the bar range - refusing to trade "
             "(this is the check that caught the first paper deploy)")

    # 2. the brain: the locked engine, replayed over the full history
    S = build_state_engine()
    tr = {}
    eq = S.simulate(bars, SYMBOL, funding=True, fund_dir=PAPER.FUNDDIR,
                    init=INIT_USDT, delta_max_pct=DELTA_MAX_PCT, track=tr,
                    **CONFIG)
    open_book = tr["open_book"]
    last_bar_ts = int(bars[-1][0])
    bar_index = last_bar_ts // TF_MS

    # 3. the exchange's actual book
    acct = ex.account()
    wallet = float(next((a["walletBalance"] for a in acct["assets"]
                         if a["asset"] == "USDT"), "0"))
    pos = ex.positions()
    oorders = ex.open_orders()
    usdt_avail = float(next((a["availableBalance"] for a in acct["assets"]
                             if a["asset"] == "USDT"), "0"))

    # 4. diff desired vs actual, trade it -----------------------------------
    # day-0 scale BEFORE any trading decision: the engine's book is at its
    # compounded replay scale, the account is at INIT_USDT. No scale, no trade.
    day0 = json.load(open(DAY0)) if os.path.exists(DAY0) else None
    if day0 is None:
        fail("no day-0 baseline - run --init first")
    scale = float(day0["scale"])

    dpos = desired_positions(open_book, scale)
    rungs, covers = desired_orders(open_book, scale)
    want_resting = {}                      # client_id -> order params
    k = 0
    for w in rungs:
        want_resting[cid(bar_index, "r", k)] = w
        k += 1
    k = 0
    for w in covers:
        want_resting[cid(bar_index, "c", k)] = w
        k += 1

    have = {o["clientOrderId"]: o for o in oorders}
    actions, errors = [], []
    n_actions = 0

    def act(desc, fn):
        nonlocal n_actions
        if n_actions >= MAX_ORDERS_PER_CYCLE:
            errors.append(f"order cap {MAX_ORDERS_PER_CYCLE} hit; {desc} deferred")
            return
        try:
            fn()
            actions.append(desc)
            n_actions += 1
        except RestError as e:
            errors.append(f"{desc}: {e.body[:120]}")

    # 4a. stale resting orders first (rung levels the engine no longer wants)
    for oid, o in have.items():
        if oid not in want_resting:
            act(f"cancel {oid} {o['side']}@{o['price']}",
                lambda oid=oid, o=o: ex.cancel(o["orderId"]))

    # 4b. position drift -> MARKET heal (the engine book is authoritative).
    # Exchange LONG/SHORT excess vs the engine book covers every flatten path
    # (stop, trend) and every refused fill the exchange took anyway.
    heal_detail = {}
    for ps, dqty in dpos.items():
        actual = abs(float(pos.get(ps, {}).get("positionAmt", 0.0) or 0.0))
        if actual > dqty + POSITION_TOL_QTY:
            q = round_qty(actual - dqty)
            side = "SELL" if ps == "LONG" else "BUY"
            act(f"heal {ps} -{q} (exchange above engine book)",
                lambda side=side, ps=ps, q=q: ex.place_market(
                    side, ps, fmt_qty(q), cid(bar_index, "h", 1 if ps == "LONG" else 2)))
            heal_detail[ps] = -q
        elif dqty > actual + POSITION_TOL_QTY:
            # the engine opened a lot the exchange missed (post-only reject,
            # partial fill...): force the book back on the engine
            q = round_qty(dqty - actual)
            side = "BUY" if ps == "LONG" else "SELL"
            act(f"heal {ps} +{q} (engine lot the exchange missed)",
                lambda side=side, ps=ps, q=q: ex.place_market(
                    side, ps, fmt_qty(q), cid(bar_index, "h", 1 if ps == "LONG" else 2)))
            heal_detail[ps] = +q

    # 4c. place missing resting orders (post-only; a GTX reject is a counted
    # recon event, retried next cycle - it must not become a market order)
    fresh = ex.open_orders() if n_actions else have
    have2 = {o["clientOrderId"] for o in fresh}
    for oid, w in want_resting.items():
        if oid in have2:
            continue
        if float(w["qty"]) <= 0:
            continue
        if float(w["qty"]) * float(w["price"]) < MIN_NOTIONAL:
            errors.append(f"{oid}: notional {float(w['qty'])*float(w['price']):.2f} "
                          f"< {MIN_NOTIONAL}; skipped")
            continue
        act(f"place {oid} {w['side']} {w['qty']}@{w['price']} ({w['kind']}, "
            f"{w['position_side']}, GTX)",
            lambda oid=oid, w=w: ex.place_limit(
                w["side"], w["position_side"], w["qty"], w["price"], oid,
                post_only=True))

    # 5. recon: engine events on NEW bars vs actual exchange fills ----------
    state = {}
    if os.path.exists(STATE):
        state = json.load(open(STATE))
    prev_book = state.get("open_book")
    done_bar = int(state.get("recon_bar", 0))
    from_id = state.get("last_trade_id")

    # first cycle after --init: probe the latest trade id WITHOUT reconning it
    # (everything before deploy is history, not forward evidence)
    if from_id is None:
        probe = ex.user_trades()
        from_id = int(max((int(t["id"]) for t in probe), default=0))
        trades, max_tid = [], from_id
    else:
        trades = ex.user_trades(from_id)
        max_tid = int(max((int(t["id"]) for t in trades), default=from_id))

    recon_events = []
    if prev_book is not None and last_bar_ts > done_bar:
        # engine rung fills on the new bar(s): rungs that vanished between the
        # previous book and this one while a matching lot appeared
        prev_rungs = {(round(float(r[0]), 6), int(r[1])) for r in prev_book["orders"]}
        now_rungs = {(round(float(r[0]), 6), int(r[1])) for r in open_book["orders"]}
        vanished = prev_rungs - now_rungs
        opened_px = {(round(float(l[1]), 6)) for l in open_book["lots"]} - \
                    {round(float(l[1]), 6) for l in prev_book["lots"]}
        engine_fills = [dict(px=p, side=s) for (p, s) in vanished if p in opened_px]
        engine_closes = [t_ for t_ in tr["trades"] if int(t_["ts"]) > done_bar]
        # exchange fills in the same window
        ex_fills = [t for t in trades
                    if int(t["time"]) > done_bar and float(t["qty"]) > 0]
        def _match(px, side, pool):
            # maker legs fill AT the engine price (2-tick window); market legs
            # (stop/trend/flatten heals) pay real slippage, so allow up to
            # 10 bps — beyond that the fill is genuinely unmatched and the
            # recon must say so
            for i, t in enumerate(pool):
                tside = 1 if t["side"] == "BUY" else -1
                tol = max(2 * TICK_SIZE, px * 0.001)
                if tside == side and abs(float(t["price"]) - px) <= tol:
                    return pool.pop(i)
            return None
        pool = list(ex_fills)
        for ef in engine_fills:
            got = _match(ef["px"], ef["side"], pool)
            recon_events.append(dict(kind="engine_fill", bar_ts=last_bar_ts,
                                     engine=dict(ef), matched=got is not None,
                                     exchange=(dict(price=got["price"],
                                                    qty=got["qty"],
                                                    commission=got["commission"])
                                               if got else None)))
        for t_ in engine_closes:
            got = _match(t_["exit"], -t_["dir"], pool)
            recon_events.append(dict(kind="engine_close", bar_ts=int(t_["ts"]),
                                     reason=t_["reason"],
                                     engine=dict(px=t_["exit"], side=-t_["dir"],
                                                 qty=t_["qty"]),
                                     matched=got is not None,
                                     exchange=(dict(price=got["price"],
                                                    qty=got["qty"],
                                                    commission=got["commission"])
                                               if got else None)))
        for t in pool:
            recon_events.append(dict(kind="exchange_only", bar_ts=last_bar_ts,
                                     exchange=dict(price=t["price"], qty=t["qty"],
                                                   side=t["side"],
                                                   commission=t["commission"])))
    matched = sum(1 for e in recon_events
                  if e["kind"] in ("engine_fill", "engine_close") and e["matched"])
    engine_total = sum(1 for e in recon_events
                       if e["kind"] in ("engine_fill", "engine_close"))

    # 6. persist recon line, state, status ----------------------------------
    rec = dict(ts_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
               net=net, bar_ts=last_bar_ts, bars=len(bars), new_bars=int(n_new),
               engine_eq=round(float(eq), 6),
               open_book=dict(state=open_book["state"],
                              center=open_book["center"], half=open_book["half"],
                              step=open_book["step"],
                              lots=len(open_book["lots"]),
                              orders=len(open_book["orders"]),
                              cooldown_left=open_book["cooldown_left"]),
               desired_positions=dpos,
               exchange_positions={p: float(pos.get(p, {}).get("positionAmt", 0.0) or 0.0)
                                   for p in ("LONG", "SHORT", "BOTH")},
               wallet_usdt=wallet, available_usdt=usdt_avail,
               actions=actions, errors=errors, heals=heal_detail,
               recon_events=recon_events, recon_matched=matched,
               recon_engine_total=engine_total)
    with open(RECON, "a") as f:
        f.write(json.dumps(rec) + "\n")

    json.dump(dict(recon_bar=last_bar_ts, last_trade_id=max_tid,
                   open_book=open_book),
              open(STATE, "w"))

    # kill rules: the engine-forward rule travels from the paper bot unchanged;
    # the LIVE-only rule is recon divergence.
    fwd_trades = [t_ for t_ in tr["trades"] if int(t_["ts"]) > int(day0["last_bar"])]
    fwd_pf, fwd_win, fwd_n = (X.metrics([t_["pnl"] for t_ in fwd_trades])
                              if fwd_trades else (None, None, 0))
    if fwd_pf is not None and not np.isfinite(fwd_pf):
        fwd_pf = None
    if fwd_n >= 30 and fwd_pf is not None and fwd_pf < 1.0:
        kill_triggered, kill_reason = True, (
            f"engine forward_pf {fwd_pf:.3f} < 1.0 on {fwd_n} lots (repo kill rule)")
    else:
        kill_triggered, kill_reason = False, (
            f"engine forward sample accumulating ({fwd_n}/30 lots)")
    # recon-based kill over the recent window
    recent = []
    if os.path.exists(RECON):
        with open(RECON) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                recent.append((r.get("recon_engine_total", 0),
                               r.get("recon_matched", 0)))
    tot = sum(a for a, _ in recent[-RECON_WINDOW:])
    mat = sum(b for _, b in recent[-RECON_WINDOW:])
    recon_match_pct = round(100.0 * mat / tot, 1) if tot else None
    if tot >= 20 and recon_match_pct is not None and \
            recon_match_pct < RECON_KILL_MATCH_PCT:
        kill_triggered = True
        kill_reason = (f"live recon fill-match {recon_match_pct}% < "
                       f"{RECON_KILL_MATCH_PCT}% over {tot} engine events")

    pf_all, _, _ = X.metrics(tr["closed_pnl"])
    status = {
        "bot": "XRP live bot", "net": net,
        "updated_utc": rec["ts_utc"],
        "mode": ("LIVE - real orders" if net == "live" else
                 "TESTNET - fake-money orders"),
        "armed": os.path.exists(ARMED),
        "sym": SYMBOL, "tf": INTERVAL, "config": CONFIG,
        "delta_max_pct": DELTA_MAX_PCT,
        "sizing": {"init_usdt": INIT_USDT, "equity_pct": EQUITY_PCT,
                   "leverage": LEVERAGE},
        "engine_sha256": ENGINE_SHA,
        "parity_ok": state_engine_fresh(),
        "funding_covers_bars": bool(covers_bars),
        "last_bar": rec["bar_ts"], "bars": len(bars),
        "funding_prints": int(n_fund),
        "engine_state": open_book["state"],
        "engine_open_lots": len(open_book["lots"]),
        "engine_resting_rungs": len(open_book["orders"]),
        "desired_positions": dpos,
        "exchange_positions": rec["exchange_positions"],
        "wallet_usdt": round(wallet, 2), "available_usdt": round(usdt_avail, 2),
        "day0_wallet_usdt": day0.get("wallet_usdt"),
        "live_pnl_usdt": (round(wallet - float(day0.get("wallet_usdt", wallet)), 2)
                          if day0.get("wallet_usdt") is not None else None),
        "actions_this_cycle": actions, "errors_this_cycle": errors,
        "recon_engine_events_total": tot, "recon_matched_total": mat,
        "recon_match_pct": recon_match_pct,
        "engine_equity": round(float(eq), 2), "account_scale": scale,
        "forward_closed_lots": int(fwd_n),
        "forward_pf": round(fwd_pf, 3) if fwd_pf is not None else None,
        "forward_win_rate_pct": round(fwd_win, 1) if fwd_win is not None else None,
        "pf_all_closed": round(pf_all, 3) if np.isfinite(pf_all) else None,
        "n_closed": len(tr["closed_pnl"]),
        "max_dd_pct": round(tr["mdd"], 2),
        "funding_paid_engine": round(float(tr["fund"]), 2),
        "fees_paid_engine": round(float(tr["fees"]), 2),
        "delta_cap_hits": int(tr["delta_cap_hits"]),
        "trend_standdown_bars": int(tr["stand_down_bars"]),
        "max_gross_leverage": round(float(np.max(tr["expo_curve"])), 2),
        "kill_criterion": ("engine forward PF < 1.0 on >= 30 lots; OR live recon "
                           f"match < {RECON_KILL_MATCH_PCT}% on >= 20 events"),
        "kill_triggered": kill_triggered, "kill_reason": kill_reason,
    }
    json.dump(status, open(STATUS, "w"), indent=1)
    print(json.dumps({k: status[k] for k in
                      ("bot", "net", "updated_utc", "engine_state",
                       "desired_positions", "exchange_positions", "wallet_usdt",
                       "actions_this_cycle", "errors_this_cycle",
                       "recon_match_pct", "kill_triggered")},
                     indent=1), flush=True)


# ── artifact (bt-artifact/1, same schema as the paper bot's forward one) ────
def save_artifact(net):
    if not os.path.exists(STATUS):
        fail("no status yet")
    status = json.load(open(STATUS))
    day0 = json.load(open(DAY0)) if os.path.exists(DAY0) else None
    k15_path = PAPER.csv_path(SYMBOL)
    fund_path = os.path.join(PAPER.FUNDDIR, f"{SYMBOL}_funding.json")
    inputs = []
    if os.path.exists(k15_path):
        inputs.append([os.path.abspath(k15_path),
                       hashlib.sha256(open(k15_path, "rb").read()).hexdigest(),
                       status.get("bars", 0)])
    if os.path.exists(fund_path):
        inputs.append([os.path.abspath(fund_path),
                       hashlib.sha256(open(fund_path, "rb").read()).hexdigest(),
                       status.get("funding_prints", 0)])
    core = {"strategy": "xrpneutral_live",
            "params": dict(CONFIG, delta_max_pct=DELTA_MAX_PCT,
                           sizing={"init_usdt": INIT_USDT,
                                   "equity_pct": EQUITY_PCT,
                                   "leverage": LEVERAGE}),
            "inputs": inputs, "engine_sha256": ENGINE_SHA,
            "engine_version": "xrp-neutral-live-1"}
    run_id = hashlib.sha256(json.dumps(
        core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
    art = {
        "schema": "bt-artifact/1", "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "strategy": "xrpneutral_live", "symbol": SYMBOL, "timeframe": INTERVAL,
        "params": core["params"],
        "provenance": {"adapter": "xrpneutral_live", "mode": f"LIVE-{net}",
                       "engine_version": "xrp-neutral-live-1",
                       "engine_files": ["xrp_neutral_engine.py",
                                        "xrp_paper_bot.py", "xrp_live_bot.py"],
                       "engine_sha256": ENGINE_SHA,
                       "note": "orders executed on Binance USDT-M; the engine "
                               "book is authoritative and the recon file is the "
                               "proof the exchange agrees"},
        "inputs": [{"path": p[0], "sha256": p[1], "bars": p[2]} for p in inputs],
        "metrics": {"net": net, "engine_state": status.get("engine_state"),
                    "desired_positions": status.get("desired_positions"),
                    "exchange_positions": status.get("exchange_positions"),
                    "wallet_usdt": status.get("wallet_usdt"),
                    "day0_wallet_usdt": (day0 or {}).get("wallet_usdt"),
                    "live_pnl_usdt": status.get("live_pnl_usdt"),
                    "forward_closed_lots": status.get("forward_closed_lots"),
                    "forward_pf": status.get("forward_pf"),
                    "recon_match_pct": status.get("recon_match_pct"),
                    "kill_triggered": status.get("kill_triggered"),
                    "kill_reason": status.get("kill_reason"),
                    "flag": ("OK" if (status.get("forward_closed_lots", 0) >= 30)
                             else "ACCUMULATING_SAMPLE")},
        "tables": [], "core": core,
        "cmd": f"python code/xrp_live_bot.py --snapshot --net {net}",
    }
    os.makedirs(ARTDIR, exist_ok=True)
    json.dump(art, open(os.path.join(ARTDIR, f"{run_id}.json"), "w"),
              indent=2, sort_keys=True)
    json.dump(art, open(os.path.join(ARTDIR, "xrp_live_latest.json"), "w"),
              indent=2, sort_keys=True)
    print(f"artifact: {os.path.join(ARTDIR, run_id + '.json')}", flush=True)


# ── CLI ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="run one cycle")
    ap.add_argument("--init", action="store_true",
                    help="exchange setup + parity + day-0 baseline")
    ap.add_argument("--status", action="store_true", help="print status only")
    ap.add_argument("--recon", action="store_true", help="print recon tail only")
    ap.add_argument("--snapshot", action="store_true", help="write artifact only")
    ap.add_argument("--arm-live", action="store_true",
                    help="interactive: arm REAL-money trading (writes ARMED)")
    ap.add_argument("--net", default="testnet", choices=sorted(NETS))
    a = ap.parse_args()

    if a.status:
        print(open(STATUS).read() if os.path.exists(STATUS) else "no status yet")
        return
    if a.recon:
        if not os.path.exists(RECON):
            print("no recon yet")
            return
        lines = open(RECON).read().strip().splitlines()
        for line in lines[-3:]:
            r = json.loads(line)
            print(json.dumps({k: r[k] for k in
                              ("ts_utc", "net", "bar_ts", "engine_state" if "engine_state" in r else "open_book",
                               "desired_positions", "exchange_positions",
                               "actions", "errors", "recon_engine_total",
                               "recon_matched")}, indent=1))
        return
    if a.snapshot:
        save_artifact(a.net)
        return

    ex = Exchange(a.net)

    if a.arm_live:
        if a.net != "live":
            fail("--arm-live only makes sense with --net live")
        print("You are about to arm REAL-MONEY trading of the XRP neutral book.")
        print(f"  engine sha256 : {ENGINE_SHA[:16]}...  (must match the verified artifact)")
        print(f"  sizing        : {INIT_USDT} USDT margin x {LEVERAGE}x, "
              f"5 levels/side, delta cap {DELTA_MAX_PCT}x equity")
        print("  kill rules    : engine forward PF < 1 on >= 30 lots; recon match "
              f"< {RECON_KILL_MATCH_PCT}% on >= 20 events")
        ans = input('Type exactly "I UNDERSTAND THIS TRADES REAL MONEY": ')
        if ans.strip() != "I UNDERSTAND THIS TRADES REAL MONEY":
            fail("not armed")
        open(ARMED, "w").write(datetime.now(timezone.utc).isoformat())
        print("ARMED written; live cycles will now place orders")
        return

    if a.init:
        os.makedirs(HOME, exist_ok=True)
        os.makedirs(PAPER.K15, exist_ok=True)
        os.makedirs(PAPER.FUNDDIR, exist_ok=True)
        ex.time_offset()
        path, _, note = PAPER.pull_klines(SYMBOL, INTERVAL, TF_MS)
        PAPER.pull_funding(SYMBOL, PAPER.FUNDING_FLOOR_MS)
        bars = PAPER.load_bars(path)
        # parity FIRST: the patched engine must equal the locked one before
        # anything else happens
        S = build_state_engine()
        parity_check(S, PAPER.FUNDDIR)
        ex.setup()
        acct = ex.account()
        wallet = float(next((x["walletBalance"] for x in acct["assets"]
                             if x["asset"] == "USDT"), "0"))
        tr = {}
        eq = S.simulate(bars, SYMBOL, funding=True, fund_dir=PAPER.FUNDDIR,
                        init=INIT_USDT, delta_max_pct=DELTA_MAX_PCT, track=tr,
                        **CONFIG)
        d0 = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "net": a.net, "sym": SYMBOL, "config": CONFIG,
              "delta_max_pct": DELTA_MAX_PCT,
              "sizing": {"init_usdt": INIT_USDT, "equity_pct": EQUITY_PCT,
                         "leverage": LEVERAGE},
              "wallet_usdt": wallet,
              "mtm_engine": float(eq), "scale": INIT_USDT / float(eq),
              "last_bar": int(bars[-1][0]),
              "open_lots": int(tr["open_lots"]),
              "n_closed": len(tr["closed_pnl"]),
              "engine_sha256": ENGINE_SHA}
        json.dump(d0, open(DAY0, "w"), indent=1)
        print(f"init ok: parity OK, exchange ready (net={a.net}), day-0 frozen: "
              f"wallet ${wallet:.2f}, engine scale {d0['scale']:.6g}, "
              f"last bar {datetime.fromtimestamp(bars[-1][0]/1000, timezone.utc).isoformat()}")
        print("NOTE: --init does NOT arm live trading; write ARMED with "
              "--arm-live --net live when the testnet stage has passed.")
        return

    if a.once:
        cycle(a.net, ex)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
