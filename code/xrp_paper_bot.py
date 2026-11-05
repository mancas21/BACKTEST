#!/usr/bin/env python3
"""
xrp_paper_bot.py — "XRP paper bot": a DELTA-NEUTRAL grid on XRPUSDT, forward paper.

WHAT IT IS
----------
A market-neutral two-sided grid on the Binance USDT-M XRPUSDT perpetual, 15m bars.
It is the FORWARD PAPER MIRROR of code/xrp_neutral_engine.py, so paper equity IS
engine equity: each cycle pulls only CLOSED bars, appends them idempotently, and
re-runs the validated engine over the full history. There is no second fill
simulator. A paper bot with its own fill model is a backtest wearing a lab coat.

PAPER ONLY. It places no orders, holds no keys, and reads no account. Binance
public REST only.

WHY NEUTRAL
------------
The validated long-grid bot is a funding PAYER ($188,284 on its XRP leg alone,
because the long side pays a positive rate in a rising market). A balanced book
pays the exchange ~nothing: the neutral book's funding over 6.5 years is $296.
That is the economic reason this bot exists, and it is measured, not asserted:
the status file carries the funding and the average net delta every cycle.

THE STRATEGY (see xrp_neutral_engine.py for the full spec and the audit)
    long ladder below the centre, short ladder above it, one step covers,
    net delta hard-capped at DELTA_MAX_PCT of equity, symmetric stand-down when
    price strays from the 1h EMA200, hard stop flattening both sides.

RUNNING
    python xrp_paper_bot.py --once          # one cycle (cron)
    python xrp_paper_bot.py --init          # freeze the Day-0 baseline
    python xrp_paper_bot.py --status        # print the status file only
    cron: */5 * * * * cd /home/ubuntu/xrp-paper-bot && ./run.sh

OUTPUTS (all prefixed xrp_paper_bot_ so it cannot be confused with the other
bots on the box)
    xrp_paper_bot_status.json    the live state
    xrp_paper_bot_day0.json      the Day-0 baseline (forward P&L is measured from it)
    xrp_paper_bot_events.csv     append-only log of closed trades
    xrp_paper_bot.log            the cron log
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

import xrp_neutral_engine as X  # noqa: E402

FAPI = "https://fapi.binance.com"
SYMBOL = "XRPUSDT"
INTERVAL = "15m"
TF_MS = 15 * 60 * 1000
LISTING_FLOOR_MS = 1567296000000          # Binance USDT-M launch
# Binance IGNORES startTime=0 (it returns the newest records instead), so the
# funding history has to be paged forward from a real early timestamp. 2017-07-14
# predates every USDT-M perp.
FUNDING_FLOOR_MS = 1500000000000
FUNDING_INTERVAL_MS = 8 * 3600 * 1000     # Binance settles funding every 8h

# Paths are relative to the BOT'S OWN directory, so the deployed bot is
# self-contained and can never read or write another bot's state. The env vars
# exist so the same code can be exercised from the research repo without
# copying 200k bars around.
HOME = os.environ.get("XRP_BOT_HOME") or HERE
DATA = os.environ.get("XRP_BOT_DATA") or os.path.join(HOME, "data")
K15 = os.path.join(DATA, "binance_klines_15m")
FUNDDIR = os.path.join(DATA, "binance_funding")

STATUS = os.path.join(HOME, "xrp_paper_bot_status.json")
DAY0 = os.path.join(HOME, "xrp_paper_bot_day0.json")
EVENTS = os.path.join(HOME, "xrp_paper_bot_events.csv")

# Same three parameters as v1: re-running the SAME pre-declared 12 cells at the
# 25 USDT x 10x sizing leaves 2 of 12 passing (PF>1.2, n>=30, 2/3 green,
# margin-safe), and this cell is the best at PF 1.302, maxDD 43.4%, max gross
# 2.14x, min margin buffer 98.9%. See code/xrp_neutral_grid_25.py and
# results/xrp_neutral_grid_25.json. Choosing DIFFERENT cell values here would be
# a new search on top of a new sizing, and would have no multiple-testing story.
CONFIG = dict(trend_band=0.10, stop_atr_mult=0.5, cover_mult=1.0)


# ── SIZING ──────────────────────────────────────────────────────────────────
# v2: 25 USDT of margin at 10x = 250 USDT of maximum gross notional. Each of the
# 5 levels per side is 100% of equity (25 USDT at inception), so a fully-filled
# two-sided ladder is exactly 10x. The grid rarely holds more than two lots at
# once, so ACTUAL gross peaks near 2x: 10x is the CEILING, not the average. That
# gap is measured every cycle (max_gross_leverage / min_margin_buffer_pct) rather
# than asserted.
#
# The delta cap MUST be >= 1x equity here. At 0.50x, the first 25 USDT fill would
# be refused and the bot could never trade. 2.0x keeps the validated book's
# lot-level bound (at most two net lots) while leaving the 10x gross reachable.
INIT_USDT = 25.0
EQUITY_PCT = 1.0
LEVERAGE = 10.0
MAINT_MARGIN = 0.005
DELTA_MAX_PCT = 2.0

# The engine file is NOT modified: EQUITY_PCT is a module global read inside
# ladder() at call time, so the sizing overlay lives here and the deployed engine
# stays byte-identical to the locked/audited one.
X.EQUITY_PCT = EQUITY_PCT


def http_json(path, params, tries=3, timeout=20):
    """Binance public REST with retries. A transient timeout must not abort a
    cycle: the next cycle re-reads the same window and catches up."""
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(FAPI + path + "?" + q,
                                 headers={"User-Agent": "xrp-paper-bot/1.0"})
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:
            last = e
            if attempt < tries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise last


# ------------------------------------------------------------------ data
def csv_path(sym):
    return os.path.join(K15, f"{sym}_15m.csv")


def read_ts(path):
    have = set()
    if os.path.exists(path):
        with open(path) as f:
            for row in csv.DictReader(f):
                try:
                    have.add(int(row["open_ts"]))
                except (ValueError, KeyError):
                    pass
    return have


def pull_klines(sym, interval, tfms, max_pages=4000):
    """Append CLOSED bars only, idempotently. A forming bar is never written, so
    the engine can never see a partially-formed candle."""
    os.makedirs(K15, exist_ok=True)
    path = csv_path(sym)
    have = read_ts(path)
    end = int(time.time() * 1000)
    new = []
    st = (max(have) + tfms) if have else None
    MIN_COVER_MS = 90 * 24 * 3600 * 1000
    span = (max(have) - min(have)) if len(have) > 1 else 0
    first = (not have) or (span < MIN_COVER_MS)
    if first and have:
        print(f"  {sym}: only {len(have)} bars spanning {span/86400000:.0f}d "
              f"- bootstrapping full history", flush=True)
    if first:
        back = end
        pages = 0
        have = set() if len(have) < 100 else have
        while pages < max_pages:
            try:
                d = http_json("/fapi/v1/klines",
                              {"symbol": sym, "interval": interval,
                               "endTime": back - 1, "limit": 1000})
            except Exception as e:
                # A bootstrap that dies mid-way must not throw away what it got.
                # Keep the bars, report the error, and let the next cycle continue
                # forward from here.
                print(f"  {sym}: bootstrap stopped after {pages} pages: "
                      f"{type(e).__name__} {str(e)[:80]}", flush=True)
                break
            if not d:
                break
            pages += 1
            oldest = int(d[0][0])
            for x in d:
                t = int(x[0])
                if t + tfms > end:
                    continue
                if t not in have:
                    new.append((t, x[1], x[2], x[3], x[4], x[5]))
                    have.add(t)
            if oldest <= LISTING_FLOOR_MS:
                break
            back = oldest
            time.sleep(0.12)
        st = None
    while st:
        params = {"symbol": sym, "interval": interval, "limit": 1000, "startTime": st}
        try:
            d = http_json("/fapi/v1/klines", params)
        except Exception as e:
            # keep what we have; the next cycle continues from the same point
            print(f"  {sym}: forward pull stopped: {type(e).__name__} {str(e)[:80]}",
                  flush=True)
            break
        if not d:
            break
        for x in d:
            t = int(x[0])
            if t + tfms > end:
                continue
            if t not in have:
                new.append((t, x[1], x[2], x[3], x[4], x[5]))
                have.add(t)
        if len(d) < 1000:
            break
        st = int(d[-1][0]) + 1
        time.sleep(0.15)
    if new:
        new.sort()
        need_hdr = (not os.path.exists(path)) or os.path.getsize(path) == 0
        with open(path, "w" if need_hdr else "a", newline="") as f:
            w = csv.writer(f)
            if need_hdr:
                w.writerow(["open_ts", "open", "high", "low", "close", "volume"])
            w.writerows(new)
    return path, len(new), "ok"


def pull_funding(sym, since_ms):
    """Refresh the real funding prints the engine charges. A book that ignores
    funding is reporting a fiction."""
    os.makedirs(FUNDDIR, exist_ok=True)
    p = os.path.join(FUNDDIR, f"{sym}_funding.json")
    cur = []
    if os.path.exists(p):
        try:
            cur = json.load(open(p, encoding="utf-8"))
        except Exception:
            cur = []
    known = {x["t"] for x in cur}
    add = []
    st = since_ms
    end = int(time.time() * 1000)
    for _ in range(60):
        try:
            d = http_json("/fapi/v1/fundingRate",
                          {"symbol": sym, "startTime": st, "endTime": end, "limit": 1000})
        except Exception as e:
            return len(cur), "REST_ERR " + str(e)[:100]
        if not d:
            break
        for x in d:
            t = int(x["fundingTime"])
            if t not in known:
                known.add(t)
                add.append({"t": t, "r": float(x["fundingRate"])})
        if len(d) < 1000:
            break
        st = int(d[-1]["fundingTime"]) + 1
        time.sleep(0.15)
    if add:
        cur.extend(add)
        cur.sort(key=lambda x: x["t"])
        json.dump(cur, open(p, "w"))
    return len(cur), "ok"


def load_bars(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append((int(r["open_ts"]), float(r["open"]), float(r["high"]),
                         float(r["low"]), float(r["close"]), float(r["volume"])))
    rows.sort(key=lambda b: b[0])
    return rows


def funding_coverage(bars, fund_dir):
    """(covers_bars, first_print_ms, last_print_ms, n_prints).

    The engine charges funding on every settlement inside the bar range. If the
    funding history does not span the bars, the early bars are silently charged
    NOTHING and the equity is quietly wrong. This is the check that would have
    caught the first deploy, where the VPS had 1,200 prints instead of 7,440 and
    reported funding_paid = -$49.96 (received) instead of +$266.14 (paid).
    """
    p = os.path.join(fund_dir, f"{SYMBOL}_funding.json")
    if not os.path.exists(p):
        return False, 0, 0, 0
    try:
        f = json.load(open(p, encoding="utf-8"))
    except Exception:
        return False, 0, 0, 0
    if not f:
        return False, 0, 0, 0
    ts = [int(x["t"]) for x in f]
    first, last = min(ts), max(ts)
    b0, b1 = int(bars[0][0]), int(bars[-1][0])
    # Funding settles every 8h, so the newest print can legitimately be up to one
    # interval behind the newest bar. What must NOT happen is a MISSING history:
    # prints that stop long before the bars end, or start long after they begin.
    covers = (first <= b0 + FUNDING_INTERVAL_MS) and (last >= b1 - FUNDING_INTERVAL_MS)
    return covers, first, last, len(ts)


def save_forward_artifact(status, bars, day0, tr, scale):
    """Saves an artifact conforming to bt-artifact/1 schema so forward results are guard-backed and verifiable."""
    import hashlib
    runs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "runs")
    os.makedirs(runs_dir, exist_ok=True)
    fwd_trades = [t_ for t_ in tr["trades"] if int(t_["ts"]) > int(day0["last_bar"])]
    k15_path = csv_path(SYMBOL)
    fund_path = os.path.join(FUNDDIR, f"{SYMBOL}_funding.json")

    inputs = []
    if os.path.exists(k15_path):
        h = hashlib.sha256(open(k15_path, "rb").read()).hexdigest()
        inputs.append([os.path.abspath(k15_path), h, len(bars)])
    if os.path.exists(fund_path):
        hf = hashlib.sha256(open(fund_path, "rb").read()).hexdigest()
        inputs.append([os.path.abspath(fund_path), hf, status["funding_prints"]])

    eng_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xrp_neutral_engine.py")
    eng_sha = hashlib.sha256(open(eng_path, "rb").read()).hexdigest()

    core = {
        "strategy": "xrpneutral_forward",
        "params": status["config"],
        "inputs": inputs,
        "engine_sha256": eng_sha,
        "engine_version": "xrp-neutral-fwd-1",
    }
    run_id = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]

    art = {
        "schema": "bt-artifact/1",
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "strategy": "xrpneutral_forward",
        "symbol": SYMBOL,
        "timeframe": INTERVAL,
        "params": status["config"],
        "provenance": {
            "adapter": "xrpneutral_forward",
            "engine_version": "xrp-neutral-fwd-1",
            "engine_files": ["xrp_neutral_engine.py", "xrp_paper_bot.py"],
            "engine_sha256": eng_sha,
            "mode": "forward-paper-live",
            "day0_utc": day0.get("created_utc"),
            "scale": scale,
            "deployed_bot": {"name": "XRP paper bot", "symbol": SYMBOL, "timeframe": INTERVAL},
        },
        "inputs": [{"path": p[0], "sha256": p[1], "bars": p[2]} for p in inputs],
        "metrics": {
            "return_pct": status["forward_pct"],
            "forward_pnl_usdt": status["forward_pnl"],
            "profit_factor": status["forward_pf"],
            "win_rate": status["forward_win_rate_pct"] / 100.0 if status["forward_win_rate_pct"] is not None else None,
            "n_trades": status["forward_closed_lots"],
            "equity": status["equity"],
            "init_usdt": status["init_usdt"],
            "max_dd_pct": status["max_dd_pct"],
            "max_gross_leverage": status["max_gross_leverage"],
            "min_margin_buffer_pct": status["min_margin_buffer_pct"],
            "NEUTRALITY_avg_abs_delta_pct": status["NEUTRALITY_avg_abs_delta_pct"],
            "kill_triggered": status["kill_triggered"],
            "kill_reason": status["kill_reason"],
            "flag": "OK" if status["forward_closed_lots"] >= 30 else "ACCUMULATING_SAMPLE",
        },
        "tables": [{"ts": t_["ts"], "side": t_["dir"], "qty": t_["qty"], "entry": t_["entry"],
                    "exit": t_["exit"], "pnl": t_["pnl"] * scale, "reason": t_["reason"]}
                   for t_ in fwd_trades],
        "core": core,
        "cmd": "python code/xrp_paper_bot.py --snapshot",
    }
    out_path = os.path.join(runs_dir, f"{run_id}.json")
    latest_path = os.path.join(runs_dir, "xrp_forward_latest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(art, f, indent=2, sort_keys=True)
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(art, f, indent=2, sort_keys=True)
    return out_path, run_id


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="run one cycle")
    ap.add_argument("--init", action="store_true", help="freeze the Day-0 baseline")
    ap.add_argument("--status", action="store_true", help="print the status file only")
    ap.add_argument("--snapshot", action="store_true", help="generate verifiable forward artifact")
    a = ap.parse_args()

    if a.status:
        print(open(STATUS, encoding="utf-8").read() if os.path.exists(STATUS) else "no status yet")
        return

    if a.init:
        path, _, note = pull_klines(SYMBOL, INTERVAL, TF_MS)
        # NOT 0: Binance ignores startTime=0 and returns the newest prints, which
        # would freeze day-0 on a partial funding history and quietly misprice the
        # baseline. Page from a real early timestamp, same as the cycle path.
        pull_funding(SYMBOL, FUNDING_FLOOR_MS)
        bars = load_bars(path)
        tr = {}
        eq = X.simulate(bars, SYMBOL, funding=True, fund_dir=FUNDDIR, init=INIT_USDT,
                        delta_max_pct=DELTA_MAX_PCT, track=tr, **CONFIG)
        d0 = {"created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "sym": SYMBOL, "config": CONFIG, "delta_max_pct": DELTA_MAX_PCT,
              "sizing": {"init_usdt": INIT_USDT, "equity_pct": EQUITY_PCT,
                         "leverage": LEVERAGE},
              # The engine replays 2020->today and COMPOUNDS, so its terminal
              # equity (millions) is not a 25 USDT account. The account is
              # NORMALISED to INIT_USDT at day-0: every USDT figure reported from
              # here on is engine_usdt * scale. Exact, because the engine is linear
              # in equity (sizing, fees, funding and the delta-cap ratio all scale).
              "mtm_engine": float(eq), "scale": INIT_USDT / float(eq),
              "mtm": INIT_USDT, "fees_engine": float(tr["fees"]),
              "fund_engine": float(tr["fund"]), "last_bar": int(bars[-1][0]),
              "open_lots": int(tr["open_lots"]),
              "n_closed": len(tr["closed_pnl"])}
        json.dump(d0, open(DAY0, "w"), indent=1)
        print(f"Day-0 baseline frozen: account ${INIT_USDT:,.2f} "
              f"(engine ${eq:,.2f}, scale {d0['scale']:.6g})  last bar "
              f"{datetime.fromtimestamp(bars[-1][0]/1000, timezone.utc).isoformat()}")
        return

    # ---- one cycle ----
    os.makedirs(HOME, exist_ok=True)
    path, n_new, note = pull_klines(SYMBOL, INTERVAL, TF_MS)
    if note != "ok":
        print(f"  kline pull failed: {note}")
        return
    # FUNDING: pull the FULL history, not a recent window. The engine charges
    # funding on every settlement inside the bar range, so a partial funding
    # history silently changes the equity -- the same strategy on two machines
    # would report different numbers. This bit us on the first deploy: the VPS
    # had 1,200 prints where the research box had 7,440, and funding_paid came
    # out as -$49.96 (received) instead of +$266.14 (paid).
    n_fund, note_f = pull_funding(SYMBOL, FUNDING_FLOOR_MS)
    if note_f != "ok":
        print(f"  funding pull failed: {note_f}")
    bars = load_bars(path)
    if len(bars) < 2000:
        print(f"  only {len(bars)} bars, not enough to run")
        return

    tr = {}
    eq = X.simulate(bars, SYMBOL, funding=True, fund_dir=FUNDDIR, init=INIT_USDT,
                    delta_max_pct=DELTA_MAX_PCT, track=tr, **CONFIG)
    covers, f_first, f_last, f_n = funding_coverage(bars, FUNDDIR)
    if not covers:
        print(f"  WARNING: funding history does NOT cover the bar range "
              f"(prints {f_n}, {datetime.fromtimestamp(f_first/1000, timezone.utc).date() if f_first else '?'}"
              f" -> {datetime.fromtimestamp(f_last/1000, timezone.utc).date() if f_last else '?'} "
              f"vs bars {datetime.fromtimestamp(bars[0][0]/1000, timezone.utc).date()}"
              f" -> {datetime.fromtimestamp(bars[-1][0]/1000, timezone.utc).date()}). "
              f"The equity below is NOT comparable with a fully-funded run.", flush=True)
    cp = tr["closed_pnl"]
    pf, win, n_closed = X.metrics(cp)
    gross = sum(abs(x) for x in cp) or 1.0
    eqc = tr["eq_curve"]
    d = tr["delta_curve"]
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.abs(d) / np.where(eqc > 0, eqc, np.nan)
    last_bar = int(bars[-1][0])
    iso = datetime.fromtimestamp(last_bar / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # The engine enforces a 96-bar cooldown after a stop (COOLDOWN_BARS). It does
    # not expose the counter in `track`, so it is inferred from the last stop:
    # exact, because the only transition into cooldown is the stop path.
    _stops = [int(t_["ts"]) for t_ in tr["trades"] if t_["reason"] == "stop"]
    last_stop = max(_stops) if _stops else 0
    cooldown_until = last_stop + 96 * TF_MS if last_stop else 0
    cooldown_left = (max(0, int((cooldown_until - last_bar + TF_MS - 1) // TF_MS))
                     if last_stop else 0)

    # Day-0 baseline: forward P&L is measured from it, so pre-existing unrealised
    # never counts as paper performance.
    day0 = {}
    if os.path.exists(DAY0):
        day0 = json.load(open(DAY0, encoding="utf-8"))
    if not day0:
        day0 = {"created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sym": SYMBOL, "config": CONFIG, "delta_max_pct": DELTA_MAX_PCT,
                "sizing": {"init_usdt": INIT_USDT, "equity_pct": EQUITY_PCT,
                           "leverage": LEVERAGE},
                "mtm_engine": float(eq), "scale": INIT_USDT / float(eq),
                "mtm": INIT_USDT, "fees_engine": float(tr["fees"]),
                "fund_engine": float(tr["fund"]), "last_bar": last_bar,
                "open_lots": int(tr["open_lots"]), "n_closed": n_closed}
        json.dump(day0, open(DAY0, "w"), indent=1)
    if "mtm_engine" not in day0:
        # A day-0 written before the account normalisation existed: its mtm WAS
        # the engine scale. Re-base it to INIT_USDT without touching the params.
        day0["mtm_engine"] = float(day0["mtm"])
        day0["scale"] = INIT_USDT / float(day0["mtm"]) if day0["mtm"] else 1.0
        day0["mtm"] = INIT_USDT
        day0["fees_engine"] = float(day0.get("fees_engine", 0.0))
        day0["fund_engine"] = float(day0.get("fund_engine", 0.0))
        json.dump(day0, open(DAY0, "w"), indent=1)
    scale = float(day0["scale"])
    eq_acct = float(eq) * scale
    fwd = (float(eq) - float(day0["mtm_engine"])) * scale
    fwd_pct = 100 * (float(eq) / max(float(day0["mtm_engine"]), 1e-9) - 1)
    fees_acct = (float(tr["fees"]) - float(day0.get("fees_engine", 0.0))) * scale
    fund_acct = (float(tr["fund"]) - float(day0.get("fund_engine", 0.0))) * scale

    # FORWARD-ONLY book: a fresh deploy must not dump six years of backtest
    # closes into the forward event log. ts is the CLOSE time, so anything at or
    # before the day-0 bar belongs to the replay, not to the paper record.
    fwd_trades = [t_ for t_ in tr["trades"] if int(t_["ts"]) > int(day0["last_bar"])]
    if fwd_trades:
        fwd_pf, fwd_win, fwd_n = X.metrics([t_["pnl"] for t_ in fwd_trades])
        fwd_closed = float(sum(t_["pnl"] for t_ in fwd_trades)) * scale
    else:
        fwd_pf, fwd_win, fwd_n, fwd_closed = None, None, 0, 0.0
    # metrics() returns +inf when there are no losing closes. Infinity is not
    # valid JSON, so the status reports null; the lot count and win rate still
    # describe the sample.
    if fwd_pf is not None and not np.isfinite(fwd_pf):
        fwd_pf = None

    # Automatic kill trigger check (repo rule: PF < 1.0 on n >= 30 closed forward trades = KILL)
    kill_criterion = "forward_pf < 1.0 on n >= 30 closed lots"
    if fwd_n >= 30:
        if fwd_pf is not None and fwd_pf < 1.0:
            kill_triggered = True
            kill_reason = f"forward_pf {fwd_pf:.3f} < 1.0 on {fwd_n} closed lots (repo kill rule)"
        else:
            kill_triggered = False
            kill_reason = None
    else:
        kill_triggered = False
        kill_reason = f"sample accumulating ({fwd_n}/30 closed lots required before kill rule applies)"

    # append-only event log of closed trades. The key includes entry/exit/pnl:
    # (ts, side) is NOT unique -- two lots on the same side can close on the same
    # bar (a cover plus a gap-through cover), and the status counts both while a
    # (ts, side) key silently drops one. That is exactly the discrepancy between
    # forward_closed_lots and this file that showed up on 2026-10-31.
    new_rows = []
    if os.path.exists(EVENTS):
        with open(EVENTS) as f:
            seen = {(r["ts"], r["side"], r["entry"], r["exit"], r["pnl"])
                    for r in csv.DictReader(f)}
    else:
        seen = set()
    for t_ in fwd_trades:
        key = (str(t_["ts"]), str(t_["dir"]), f"{t_['entry']:.8f}",
               f"{t_['exit']:.8f}", f"{t_['pnl']:.6f}")
        if key in seen:
            continue
        seen.add(key)
        new_rows.append([t_["ts"], t_["dir"], f"{t_['qty']:.6f}", f"{t_['entry']:.8f}",
                         f"{t_['exit']:.8f}", f"{t_['pnl']:.6f}", t_["reason"]])
    if new_rows:
        need = (not os.path.exists(EVENTS)) or os.path.getsize(EVENTS) == 0
        with open(EVENTS, "a", newline="") as f:
            w = csv.writer(f)
            if need:
                w.writerow(["ts", "side", "qty", "entry", "exit", "pnl", "reason"])
            w.writerows(new_rows)

    status = {
        "bot": "XRP paper bot",
        "updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "PAPER - no orders are placed, no keys are read, Binance public REST only",
        "sym": SYMBOL, "tf": INTERVAL, "config": CONFIG,
        "delta_max_pct": DELTA_MAX_PCT,
        "sizing": {"init_usdt": INIT_USDT, "equity_pct": EQUITY_PCT,
                   "leverage": LEVERAGE},
        "account_note": "USDT fields are normalised to an INIT_USDT day-0 account; "
                        "engine_equity is the raw compounded replay scale",
        "last_bar": iso, "new_15m_bars": int(n_new), "funding_prints": int(n_fund),
        "last_stop_utc": (datetime.fromtimestamp(last_stop / 1000, timezone.utc)
                          .strftime("%Y-%m-%dT%H:%M:%SZ") if last_stop else None),
        "cooldown_until_utc": (datetime.fromtimestamp(cooldown_until / 1000, timezone.utc)
                               .strftime("%Y-%m-%dT%H:%M:%SZ") if last_stop else None),
        "cooldown_bars_left": int(cooldown_left),
        "bars": len(bars),
        "equity": round(eq_acct, 2),
        "init_usdt": INIT_USDT,
        "net_from_inception_pct": round(fwd_pct, 3),
        "forward_pnl": round(fwd, 2), "forward_pct": round(fwd_pct, 3),
        "forward_closed_lots": int(fwd_n),
        "forward_closed_pnl": round(fwd_closed, 4),
        "forward_pf": round(fwd_pf, 3) if fwd_pf is not None else None,
        "forward_win_rate_pct": round(fwd_win, 1) if fwd_win is not None else None,
        "kill_criterion": kill_criterion,
        "kill_triggered": kill_triggered,
        "kill_reason": kill_reason,
        "engine_equity": round(float(eq), 2),
        "account_scale": scale,
        "engine_full_history_pct": round(100 * (float(eq) / INIT_USDT - 1), 2),
        "day0_utc": day0.get("created_utc"),
        "pf_all_closed": round(pf, 3), "n_closed": n_closed,
        "win_rate_pct": round(win, 1),
        "max_dd_pct": round(tr["mdd"], 2),
        "fees_paid": round(fees_acct, 4),
        "funding_paid": round(fund_acct, 4),
        "fees_paid_engine": round(float(tr["fees"]), 2),
        "funding_paid_engine": round(float(tr["fund"]), 2),
        "commission_gross_pct": round(100 * tr["fees"] / gross, 2),
        "funding_attached": True, "funding_covers_bars": bool(covers),
        "funding_first_print": (datetime.fromtimestamp(f_first / 1000, timezone.utc)
                                .strftime("%Y-%m-%dT%H:%M:%SZ") if f_first else None),
        "funding_last_print": (datetime.fromtimestamp(f_last / 1000, timezone.utc)
                               .strftime("%Y-%m-%dT%H:%M:%SZ") if f_last else None),
        "open_lots": int(tr["open_lots"]),
        "grids_built": int(tr["grids"]), "fills": int(tr["fills"]),
        "cycles": int(tr["cycles"]),
        "NEUTRALITY_avg_abs_delta_pct": round(float(np.nanmean(ratio) * 100), 3),
        "NEUTRALITY_max_abs_delta_pct": round(float(np.nanmax(ratio) * 100), 3),
        "delta_cap_hits": int(tr["delta_cap_hits"]),
        "trend_standdown_bars": int(tr["stand_down_bars"]),
        # 10x is a ceiling, so it is measured, not claimed.
        "max_gross_leverage": round(float(np.max(tr["expo_curve"])), 2),
        "min_margin_buffer_pct": round(float(np.min(
            (eqc - MAINT_MARGIN * np.asarray(tr["gross_curve"], float))
            / np.maximum(eqc, 1e-12)) * 100.0), 1),
        "exit_reasons": tr["reasons"],
        "buyhold_pct": round(100 * (bars[-1][4] / bars[0][4] - 1), 1),
        "new_trades_logged": len(new_rows),
    }
    art_path, art_id = save_forward_artifact(status, bars, day0, tr, scale)
    status["forward_artifact"] = art_path
    status["forward_run_id"] = art_id
    json.dump(status, open(STATUS, "w"), indent=1)
    print(json.dumps(status, indent=1), flush=True)


if __name__ == "__main__":
    main()
