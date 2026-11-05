#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Polymarket Phase-1 data recorder (public API, paper only, no keys).

Watches the Polymarket hourly crypto "Up or Down" series (BTC/ETH/XRP
verified live 2026-10-22) and records, append-only, under --data-dir:

  <series_slug>/snapshots_YYYYMMDD.csv   one row per token per sampling round
  <series_slug>/books_YYYYMMDD.jsonl     full CLOB order book (both tokens) per round
  <series_slug>/settlements.csv          settled markets, idempotent, with a
                                         raw-Binance-candle cross-check
  manifest.json                          heartbeat + counters for staleness watchdogs

Endpoints used (all public, no auth):
  Gamma   https://gamma-api.polymarket.com/events?series_slug=<s>&closed=false|true
  CLOB    https://clob.polymarket.com/book?token_id=<id>
          https://clob.polymarket.com/time
  Binance https://api.binance.com/api/v3/ticker/price?symbol=<SYM>
          https://api.binance.com/api/v3/klines?symbol=<SYM>&interval=1h&...

Cadence policy:
  - markets with -RECENT <= seconds_left <= FAST_WINDOW: every --interval (fast)
  - pre-open markets within --preopen-hours of their candle: once per --refresh
  - settlements polled every --settle-every, only umaResolutionStatus "resolved"

Snapshot CSV depth columns dep_*_w1/w2/w5 are the summed size within
|price - best| <= 0.01 / 0.02 / 0.05 of the best level on that side.

Fee fields are RECORDED RAW, never interpreted: fee_type/fee_rate/fee_rebate/
fee_taker_only/maker_base_fee_bps/taker_base_fee_bps. Any replay backtest must
implement Polymarket's actual taker-fee formula after reading the venue fee
documentation; this recorder deliberately does not model a fee.

This script records. It places no orders and needs no Ethereum address.
Usage:
  python code\\poly_recorder.py --once
  python code\\poly_recorder.py --duration 300 --interval 6
"""

import argparse
import csv
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REC_VERSION = "poly-recorder/1.0"

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"
BINANCE_BASE = "https://api.binance.com"

DEFAULT_SERIES = [
    "btc-up-or-down-hourly",
    "eth-up-or-down-hourly",
    "xrp-up-or-down-hourly",
]

# series slug prefix (before "-up-or-down-hourly") -> Binance spot symbol
ASSET_TO_BINANCE = {
    "btc": "BTCUSDT",
    "eth": "ETHUSDT",
    "xrp": "XRPUSDT",
    "sol": "SOLUSDT",   # unprobed fallback, harmless if unused
    "doge": "DOGEUSDT",
    "link": "LINKUSDT",
}

SNAPSHOT_COLS = [
    "ts", "ts_epoch", "clob_ts_ms", "drift_ms", "series_slug", "market_slug",
    "outcome", "token_id", "event_start", "event_end", "seconds_left",
    "price_to_beat", "final_price", "tick_size", "min_order_size",
    "last_trade_price", "best_bid", "best_bid_sz", "best_ask", "best_ask_sz",
    "spread", "mid", "n_bid", "n_ask",
    "dep_bid_w1", "dep_bid_w2", "dep_bid_w5",
    "dep_ask_w1", "dep_ask_w2", "dep_ask_w5",
    "spot", "binance_1h_open", "binance_1h_open_time", "binance_1h_prev_close",
    "fee_type", "fee_rate", "fee_rebate", "fee_taker_only",
    "maker_base_fee_bps", "taker_base_fee_bps", "rec_version",
]

SETTLEMENT_COLS = [
    "ts_recorded", "series_slug", "market_slug", "event_start", "event_end",
    "winner", "outcome_prices", "price_to_beat", "final_price", "closed_time",
    "uma_status", "binance_1h_open", "binance_1h_close", "binance_1h_open_time",
    "binance_winner", "winner_matches_binance", "rec_version",
]


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def fnum(x):
    """Parse a numeric value safely; '' when missing/unparsable."""
    try:
        if x is None or x == "":
            return ""
        return float(x)
    except (TypeError, ValueError):
        return ""


def http_get_json(url, timeout=10, attempts=2):
    last_err = None
    for _ in range(attempts):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": REC_VERSION,
                              "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError,
                TimeoutError, OSError, ValueError) as exc:
            last_err = exc
            time.sleep(0.5)
    raise RuntimeError("GET failed %s: %r" % (url, last_err))


def parse_book_levels(book):
    bids, asks = [], []
    for t in book.get("bids") or []:
        p, s = fnum(t.get("price")), fnum(t.get("size"))
        if p != "" and s != "":
            bids.append((p, s))
    for t in book.get("asks") or []:
        p, s = fnum(t.get("price")), fnum(t.get("size"))
        if p != "" and s != "":
            asks.append((p, s))

    def agg(levels, is_bid):
        if not levels:
            return "", "", 0, "", "", ""
        best = max(p for p, _ in levels) if is_bid else min(p for p, _ in levels)
        best_sz = sum(s for p, s in levels if abs(p - best) < 1e-9)
        n = len(levels)
        deps = []
        for w in (0.01, 0.02, 0.05):
            if is_bid:
                deps.append(sum(s for p, s in levels if best - p <= w + 1e-9))
            else:
                deps.append(sum(s for p, s in levels if p - best <= w + 1e-9))
        return best, best_sz, n, deps[0], deps[1], deps[2]

    bb, bs, nb, db1, db2, db5 = agg(bids, True)
    ba, asz, na, da1, da2, da5 = agg(asks, False)
    if ba != "" and bb != "":
        spread = ba - bb
        mid = (ba + bb) / 2.0
    else:
        spread, mid = "", ""
    return dict(bids=bids, asks=asks, bb=bb, bs=bs, ba=ba, asz=asz,
                nb=nb, na=na, db1=db1, db2=db2, db5=db5,
                da1=da1, da2=da2, da5=da5, spread=spread, mid=mid)


def parse_market(event, expected_series):
    """Extract the single market (markets[0]) from a Gamma event dict."""
    mkts = event.get("markets") or []
    if not mkts:
        return None
    m = mkts[0]
    try:
        outcomes = json.loads(m.get("outcomes") or "[]")
        tokens = json.loads(m.get("clobTokenIds") or "[]")
    except ValueError:
        return None
    if len(outcomes) != 2 or len(tokens) != 2:
        return None
    fee = m.get("feeSchedule") or {}
    return {
        "series_slug": expected_series,
        "market_slug": m.get("slug") or event.get("slug"),
        "outcome_a": str(outcomes[0]),
        "outcome_b": str(outcomes[1]),
        "token_a": str(tokens[0]),
        "token_b": str(tokens[1]),
        "event_start": m.get("eventStartTime") or "",
        "event_end": m.get("endDate") or event.get("endDate") or "",
        "tick_size": fnum(m.get("orderPriceMinTickSize")),
        "min_order_size": fnum(m.get("orderMinSize")),
        "fee_type": m.get("feeType") or "",
        "fee_rate": fnum(fee.get("rate")),
        "fee_rebate": fnum(fee.get("rebateRate")),
        "fee_taker_only": fee.get("takerOnly"),
        "maker_base_fee_bps": fnum(m.get("makerBaseFee")),
        "taker_base_fee_bps": fnum(m.get("takerBaseFee")),
        "uma_status": m.get("umaResolutionStatus") or "",
    }


def parse_ts(s):
    """Gamma ISO timestamps -> epoch seconds (naive strings are UTC)."""
    if not s:
        return None
    try:
        if s.endswith("Z"):
            return datetime.datetime.fromisoformat(s[:-1] + "+00:00").timestamp()
        return datetime.datetime.fromisoformat(s).replace(
            tzinfo=datetime.timezone.utc).timestamp()
    except ValueError:
        return None


def asset_of(series_slug):
    prefix = series_slug.split("-")[0].lower()
    return prefix, ASSET_TO_BINANCE.get(prefix)


def binance_spot_klines(symbol, now_epoch):
    """(spot, current_1h_open, current_1h_open_time, prev_1h_close)."""
    spot = cur_open = cur_open_t = prev_close = ""
    if not symbol:
        return spot, cur_open, cur_open_t, prev_close
    try:
        j = http_get_json(BINANCE_BASE + "/api/v3/ticker/price?symbol="
                          + urllib.parse.quote(symbol))
        spot = fnum(j.get("price"))
    except (RuntimeError, ValueError):
        pass
    try:
        ms = int(now_epoch * 1000)
        j = http_get_json(
            BINANCE_BASE + "/api/v3/klines?symbol=" + urllib.parse.quote(symbol)
            + "&interval=1h&limit=2")
        for row in j:
            ot_ms = int(row[0])
            if ot_ms <= ms < ot_ms + 3600_000:
                cur_open_t = ot_ms / 1000.0
                cur_open = fnum(row[1])
            else:
                prev_close = fnum(row[4])
        if cur_open == "" and j:   # boundary edge: newest row is the current candle
            row = j[-1]
            cur_open_t = int(row[0]) / 1000.0
            cur_open = fnum(row[1])
    except (RuntimeError, ValueError, IndexError, KeyError):
        pass
    return spot, cur_open, cur_open_t, prev_close


def binance_candle_at(symbol, candle_open_epoch):
    """(open, close, open_time) of the 1h candle whose openTime equals
    candle_open_epoch. NEEDED SUBTLETY: Binance klines "startTime" returns
    candles with openTime >= startTime, so the candle must be addressed by
    its OWN open time; querying near end-of-candle returns the NEXT candle.
    openTime is echoed so the caller (and any later audit) can verify the
    alignment instead of trusting this call."""
    if not symbol:
        return "", "", ""
    try:
        url = (BINANCE_BASE + "/api/v3/klines?symbol="
               + urllib.parse.quote(symbol) + "&interval=1h&startTime="
               + str(int(candle_open_epoch * 1000)) + "&limit=1")
        j = http_get_json(url)
        if not j:
            return "", "", ""
        row = j[0]
        ot = int(row[0]) / 1000.0
        if abs(ot - candle_open_epoch) > 1.0:
            return "", "", ot   # misaligned: echo ot for audit, blank values
        return fnum(row[1]), fnum(row[4]), ot
    except (RuntimeError, ValueError, IndexError, KeyError):
        return "", "", ""


class Recorder:
    def __init__(self, args):
        self.args = args
        self.data_dir = args.data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.series = list(args.series)
        self.live = []              # discovery cache of parsed markets
        self.discovery_ts = 0.0
        self.settle_ts = 0.0
        self.settled_seen = set()   # market_slug already written to settlements.csv
        self.rounds = 0
        self.snapshots_written = 0
        self.books_written = 0
        self.settlements_written = 0
        self.errors_total = 0
        self.errors_last_round = 0
        self._load_settlements_seen()

    # ---------- file plumbing ----------

    def _append_csv(self, path, cols, row):
        new = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(cols)
            w.writerow([row.get(c, "") for c in cols])
        if new:
            print("created %s" % path)

    def _series_dir(self, series_slug):
        d = os.path.join(self.data_dir, series_slug)
        os.makedirs(d, exist_ok=True)
        return d

    def _load_settlements_seen(self):
        for s in self.series:
            path = os.path.join(self._series_dir(s), "settlements.csv")
            if not os.path.exists(path):
                continue
            with open(path, newline="", encoding="utf-8-sig") as fh:
                for row in csv.DictReader(fh):
                    slug = row.get("market_slug")
                    if slug:
                        self.settled_seen.add(slug)

    def manifest_write(self, last_error=""):
        payload = {
            "rec_version": REC_VERSION,
            "last_round_ts": iso(utcnow()),
            "rounds": self.rounds,
            "snapshots_written": self.snapshots_written,
            "books_written": self.books_written,
            "settlements_written": self.settlements_written,
            "errors_total": self.errors_total,
            "errors_last_round": self.errors_last_round,
            "last_error": last_error[:300],
            "series": self.series,
            "interval_s": self.args.interval,
        }
        with open(os.path.join(self.data_dir, "manifest.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)

    # ---------- discovery ----------

    def discover(self, now_epoch):
        found = []
        for s in self.series:
            try:
                url = (GAMMA_BASE + "/events?series_slug="
                       + urllib.parse.quote(s) + "&closed=false&limit=50")
                events = http_get_json(url)
            except (RuntimeError, ValueError) as exc:
                self.errors_total += 1
                self.errors_last_round += 1
                print("discovery error %s: %r" % (s, exc))
                continue
            if not events:
                print("series %s returned no open events" % s)
            for ev in events or []:
                if ev.get("seriesSlug") != s:
                    continue   # trust-but-verify: keep only exact-series events
                mk = parse_market(ev, s)
                if not mk:
                    continue
                try:
                    meta = ev.get("eventMetadata") or {}
                    mk["price_to_beat"] = fnum(meta.get("priceToBeat"))
                    mk["final_price"] = fnum(meta.get("finalPrice"))
                    json.dumps(mk)   # must be serialisable for safety
                except (TypeError, ValueError):
                    self.errors_total += 1
                    self.errors_last_round += 1
                    print("unserialisable market skipped: %r" % mk.get("market_slug"))
                    continue
                found.append(mk)
        self.live = found
        self.discovery_ts = now_epoch
        ends = sorted(mk["event_end"] for mk in self.live if mk["event_end"])
        print("discovery: %d open markets, %d series; end range %s .. %s"
              % (len(self.live), len(self.series),
                 ends[0] if ends else "-", ends[-1] if ends else "-"))

    # ---------- sampling ----------

    def sample_targets(self, now_epoch):
        """Markets to fetch this round: the fast window around expiry always;
        pre-open within --preopen-hours only on discovery rounds."""
        refresh_round = (now_epoch - self.discovery_ts) <= 1.0
        out = []
        for mk in self.live:
            end = parse_ts(mk["event_end"])
            if end is None:
                continue
            sec_left = end - now_epoch
            if sec_left < -self.args.recent_window:
                continue
            in_fast = -self.args.recent_window <= sec_left <= self.args.fast_window
            start = parse_ts(mk["event_start"])
            preopen = (start is not None
                       and sec_left > self.args.fast_window
                       and (start - now_epoch) <= self.args.preopen_hours * 3600.0)
            if in_fast or (preopen and refresh_round):
                out.append(mk)
        return out

    def snapshot_one(self, mk, spot_kl, now_epoch, drift_ms):
        sdir = self._series_dir(mk["series_slug"])
        end = parse_ts(mk["event_end"])
        sec_left = (end - now_epoch) if end is not None else ""
        spot, cur_open, cur_open_t, prev_close = spot_kl
        day = utcnow().strftime("%Y%m%d")
        spath = os.path.join(sdir, "snapshots_%s.csv" % day)
        bpath = os.path.join(sdir, "books_%s.jsonl" % day)

        for outcome, token in ((mk["outcome_a"], mk["token_a"]),
                               (mk["outcome_b"], mk["token_b"])):
            try:
                bk = http_get_json(CLOB_BASE + "/book?token_id="
                                   + urllib.parse.quote(token))
            except (RuntimeError, ValueError) as exc:
                self.errors_total += 1
                self.errors_last_round += 1
                print("book error %s/%s: %r" % (mk["market_slug"], outcome, exc))
                continue
            lv = parse_book_levels(bk)

            def fmt(x, nd):
                return ("%.2f" % x) if x != "" else ""

            row = {
                "ts": iso(utcnow()),
                "ts_epoch": "%.3f" % time.time(),
                "clob_ts_ms": bk.get("timestamp") or "",
                "drift_ms": drift_ms,
                "series_slug": mk["series_slug"],
                "market_slug": mk["market_slug"],
                "outcome": outcome,
                "token_id": token,
                "event_start": mk["event_start"],
                "event_end": mk["event_end"],
                "seconds_left": ("%.1f" % sec_left) if sec_left != "" else "",
                "price_to_beat": mk["price_to_beat"],
                "final_price": mk["final_price"],
                "tick_size": mk["tick_size"],
                "min_order_size": mk["min_order_size"],
                "last_trade_price": fnum(bk.get("last_trade_price")),
                "best_bid": lv["bb"], "best_bid_sz": lv["bs"],
                "best_ask": lv["ba"], "best_ask_sz": lv["asz"],
                "spread": fmt(lv["spread"], 4),
                "mid": fmt(lv["mid"], 4),
                "n_bid": lv["nb"], "n_ask": lv["na"],
                "dep_bid_w1": fmt(lv["db1"], 2),
                "dep_bid_w2": fmt(lv["db2"], 2),
                "dep_bid_w5": fmt(lv["db5"], 2),
                "dep_ask_w1": fmt(lv["da1"], 2),
                "dep_ask_w2": fmt(lv["da2"], 2),
                "dep_ask_w5": fmt(lv["da5"], 2),
                "spot": spot,
                "binance_1h_open": cur_open,
                "binance_1h_open_time":
                    ("%.0f" % cur_open_t) if cur_open_t != "" else "",
                "binance_1h_prev_close": prev_close,
                "fee_type": mk["fee_type"],
                "fee_rate": mk["fee_rate"],
                "fee_rebate": mk["fee_rebate"],
                "fee_taker_only": mk["fee_taker_only"],
                "maker_base_fee_bps": mk["maker_base_fee_bps"],
                "taker_base_fee_bps": mk["taker_base_fee_bps"],
                "rec_version": REC_VERSION,
            }
            self._append_csv(spath, SNAPSHOT_COLS, row)
            self.snapshots_written += 1

            jline = {
                "ts": row["ts"], "ts_epoch": row["ts_epoch"],
                "clob_timestamp_ms": row["clob_ts_ms"],
                "series_slug": mk["series_slug"],
                "market_slug": mk["market_slug"],
                "outcome": outcome, "token_id": token,
                "hash": bk.get("hash") or "",
                "market": bk.get("market") or "",
                "neg_risk": bk.get("neg_risk"),
                "tick_size": fnum(bk.get("tick_size")),
                "min_order_size": fnum(bk.get("min_order_size")),
                "last_trade_price": fnum(bk.get("last_trade_price")),
                "bids": [[p, s] for p, s in lv["bids"]],
                "asks": [[p, s] for p, s in lv["asks"]],
            }
            with open(bpath, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(jline, separators=(",", ":")) + "\n")
            self.books_written += 1
            time.sleep(0.15)   # pace public endpoints

    # ---------- settlements ----------

    def settle_round(self, now_epoch):
        for s in self.series:
            _, bsym = asset_of(s)
            try:
                url = (GAMMA_BASE + "/events?series_slug=" + urllib.parse.quote(s)
                       + "&closed=true&order=endDate&ascending=false&limit=30")
                events = http_get_json(url)
            except (RuntimeError, ValueError) as exc:
                self.errors_total += 1
                self.errors_last_round += 1
                print("settlement error %s: %r" % (s, exc))
                continue
            sdir = self._series_dir(s)
            for ev in events or []:
                if ev.get("seriesSlug") != s:
                    continue
                mk = parse_market(ev, s)
                if not mk or mk["market_slug"] in self.settled_seen:
                    continue
                m = (ev.get("markets") or [{}])[0]
                if (m.get("umaResolutionStatus") or "") != "resolved":
                    continue   # "proposed" can still flip; only record resolved
                try:
                    prices = json.loads(m.get("outcomePrices") or "[]")
                except ValueError:
                    continue
                if not (isinstance(prices, list) and len(prices) == 2):
                    continue
                pa, pb = fnum(prices[0]), fnum(prices[1])
                if pa >= 0.999 and pb <= 0.001:
                    winner = mk["outcome_a"]
                elif pb >= 0.999 and pa <= 0.001:
                    winner = mk["outcome_b"]
                else:
                    continue
                meta = ev.get("eventMetadata") or {}
                end_ts = parse_ts(ev.get("endDate") or m.get("endDate"))
                bo, bc, bot = "", "", ""
                if end_ts:
                    bo, bc, bot = binance_candle_at(bsym, end_ts - 3600.0)
                bin_winner = ""
                match = ""
                if bo != "" and bc != "":
                    bin_winner = "Up" if (bc >= bo) else "Down"
                    match = "1" if bin_winner == winner else "0"
                row = {
                    "ts_recorded": iso(utcnow()),
                    "series_slug": s,
                    "market_slug": mk["market_slug"],
                    "event_start": m.get("eventStartTime") or "",
                    "event_end": ev.get("endDate") or m.get("endDate") or "",
                    "winner": winner,
                    "outcome_prices": json.dumps(prices),
                    "price_to_beat": fnum(meta.get("priceToBeat")),
                    "final_price": fnum(meta.get("finalPrice")),
                    "closed_time": m.get("closedTime") or ev.get("closedTime") or "",
                    "uma_status": m.get("umaResolutionStatus") or "",
                    "binance_1h_open": bo,
                    "binance_1h_close": bc,
                    "binance_1h_open_time":
                        ("%.0f" % bot) if bot != "" else "",
                    "binance_winner": bin_winner,
                    "winner_matches_binance": match,
                    "rec_version": REC_VERSION,
                }
                self._append_csv(os.path.join(sdir, "settlements.csv"),
                                 SETTLEMENT_COLS, row)
                self.settled_seen.add(mk["market_slug"])
                self.settlements_written += 1
                print("settled %s winner=%s binance=%s" %
                      (mk["market_slug"], winner, bin_winner or "?"))
            time.sleep(0.2)

    # ---------- main loop ----------

    def tick(self):
        self.errors_last_round = 0
        now_epoch = time.time()
        self.rounds += 1

        # clock drift vs CLOB (a data-quality column the replay will need)
        drift_ms = ""
        try:
            ts = http_get_json(CLOB_BASE + "/time", attempts=1)
            drift_ms = int(float(ts) * 1000 - now_epoch * 1000)
        except (RuntimeError, ValueError, TypeError):
            self.errors_total += 1
            self.errors_last_round += 1

        if now_epoch - self.discovery_ts >= self.args.refresh:
            self.discover(now_epoch)

        targets = self.sample_targets(now_epoch)

        # shared spot/klines per asset, one call set per asset per round
        cache = {}
        for mk in targets:
            prefix, bsym = asset_of(mk["series_slug"])
            if prefix in cache:
                continue
            cache[prefix] = binance_spot_klines(bsym, now_epoch)

        by_prefix = {}
        for mk in targets:
            prefix, _ = asset_of(mk["series_slug"])
            by_prefix.setdefault(prefix, []).append(mk)

        for prefix in sorted(by_prefix):
            for mk in by_prefix[prefix]:
                try:
                    self.snapshot_one(mk, cache.get(prefix, ("", "", "", "")),
                                      now_epoch, drift_ms)
                except (RuntimeError, ValueError, KeyError) as exc:
                    self.errors_total += 1
                    self.errors_last_round += 1
                    print("snapshot error %s: %r" % (mk.get("market_slug"), exc))

        if now_epoch - self.settle_ts >= self.args.settle_every:
            self.settle_ts = now_epoch
            self.settle_round(now_epoch)

        pruned = [mk for mk in self.live
                  if parse_ts(mk["event_end"]) is not None
                  and parse_ts(mk["event_end"]) < now_epoch - self.args.recent_window]
        if pruned:
            self.live = [mk for mk in self.live if mk not in pruned]
            print("pruned %d expired markets from live cache" % len(pruned))

        print("round %d: %d live, sampled %d, snap %d, books %d, settled %d, "
              "errors %d (drift %s ms)" % (
                  self.rounds, len(self.live), len(targets),
                  self.snapshots_written, self.books_written,
                  self.settlements_written, self.errors_last_round, drift_ms))
        self.manifest_write()   # heartbeat AFTER round bookkeeping; watchdogs read this

    def run(self):
        print("%s starting; data dir %s" % (REC_VERSION, self.data_dir))
        deadline = time.time() + self.args.duration if self.args.duration else None
        try:
            while True:
                self.tick()
                if self.args.once:
                    break
                if deadline and time.time() >= deadline:
                    break
                time.sleep(self.args.interval)
        finally:
            self.manifest_write()


def main():
    ap = argparse.ArgumentParser(
        description="Polymarket Phase-1 Up/Down data recorder (paper, keyless)")
    ap.add_argument("--data-dir", default="data/polymarket")
    ap.add_argument("--series", action="append", default=None)
    ap.add_argument("--interval", type=float, default=6.0,
                    help="seconds between sampling rounds")
    ap.add_argument("--refresh", type=float, default=120.0,
                    help="seconds between Gamma discovery refreshes")
    ap.add_argument("--settle-every", type=float, default=120.0)
    ap.add_argument("--fast-window", type=float, default=3600.0,
                    help="seconds before expiry to sample fast")
    ap.add_argument("--recent-window", type=float, default=900.0,
                    help="seconds after expiry to keep sampling")
    ap.add_argument("--preopen-hours", type=float, default=4.0,
                    help="hours of pre-open lookahead to sample (slow cadence)")
    ap.add_argument("--duration", type=float, default=0.0,
                    help="0 = run forever; else stop after N seconds")
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    a.series = a.series or DEFAULT_SERIES
    a.duration = max(0.0, a.duration)
    if a.once:
        a.duration = 0.0
    rec = Recorder(a)
    try:
        rec.run()
    except KeyboardInterrupt:
        print("interrupted; manifest written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
