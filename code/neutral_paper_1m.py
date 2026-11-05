#!/usr/bin/env python3
"""neutral_paper_1m.py — forward paper with 1m fill accounting.

Same five isolated pair instances, same day-0 baseline, same strategy; the ONLY
change is the fill model. Each cycle pulls closed bars, appends them
idempotently, and re-runs the engine over the full history, exactly as the 15m
runner does. There is no second fill simulator.

WHAT "1m ACCOUNTING" MEANS HERE
-------------------------------
code/xrp_neutral_engine_paper_1m.py resolves a 15m bar minute by minute when its
1m tape is COMPLETE (>= 15 distinct minutes): entries and covers fill in 1m
temporal order, and a cover may fill only on a STRICTLY LATER minute than its own
entry. A same-minute touch is unresolvable from OHLC: it is counted and banned,
never assumed. Every bar without a complete tape keeps the original same-bar
model, which is why the pre-day-0 history — and therefore the day-0 baseline —
cannot move.

The tape is fetched from day0.last_bar + 15m, so the day-0 bar itself has no
tape and stays on the 15m convention. The forward window is the only place the
fill model changes; `one_m.forward_coverage_pct` states how much of it is
actually resolved. A partial tape (a fetch gap) falls back and is COUNTED, not
hidden: `forward_coverage_ok` is false and the cycle says so.

PAPER ONLY. It places no orders, holds no keys and reads no account. Binance
public REST only.

OUTPUTS (suffixed _1m so the 15m record stays intact)
    xrp_paper_bot_status_1m.json   the live 1m state (+ vs_15m comparison)
    xrp_paper_bot_events_1m.csv    append-only log of closed trades
    runs/<id>.json                 forward artifact (bt-artifact/1)

The day-0 file is SHARED with the 15m bot (xrp_paper_bot_day0.json): the two
records must be measured from the same account baseline to be comparable.

RUNNING
    python neutral_paper_1m.py --once       # one cycle (cron)
    python neutral_paper_1m.py --dry-run    # read local files, no fetch/no writes
    python neutral_paper_1m.py --status     # print the status file only
"""
from __future__ import annotations

import argparse
import csv
import hashlib
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

import xrp_neutral_engine_paper_1m as X  # noqa: E402

FAPI = "https://fapi.binance.com"
SYMBOL = os.environ.get("NEUTRAL_SYMBOL", "XRPUSDT")
BOT_LABEL = os.environ.get("NEUTRAL_LABEL", "XRP neutral paper bot (1m)")
INTERVAL = "15m"
TF_MS = 15 * 60 * 1000
ONE_M_MS = 60 * 1000
FUNDING_FLOOR_MS = 1500000000000
FUNDING_INTERVAL_MS = 8 * 3600 * 1000

HOME = os.environ.get("XRP_BOT_HOME") or HERE
DATA = os.environ.get("XRP_BOT_DATA") or os.path.join(HOME, "data")
K15 = os.path.join(DATA, "binance_klines_15m")
K1 = os.path.join(DATA, "binance_klines_1m")
FUNDDIR = os.path.join(DATA, "binance_funding")

STATUS = os.path.join(HOME, "xrp_paper_bot_status_1m.json")
STATUS_15 = os.path.join(HOME, "xrp_paper_bot_status.json")
DAY0 = os.path.join(HOME, "xrp_paper_bot_day0.json")
DAY0_CHECK = os.path.join(HOME, "xrp_paper_bot_day0_1m_check.json")
EVENTS = os.path.join(HOME, "xrp_paper_bot_events_1m.csv")

ENGINE_FILE = os.path.join(HERE, "xrp_neutral_engine_paper_1m.py")

CONFIG = dict(trend_band=0.10, stop_atr_mult=0.5, cover_mult=1.0)

# sha256 of code/xrp_neutral_engine_paper.py, byte-identical to the 15m engine
# deployed in every pair directory as xrp_neutral_engine.py. The 1m engine is
# GENERATED from it by code/_neutral_1m_build.py.
BASE_ENGINE_SHA = "834f3de9f5d0dddd3a5b13f4a881995643b35d0f485200336df19d1c71b74776"

INIT_USDT = 25.0
EQUITY_PCT = 1.0
LEVERAGE = 10.0
MAINT_MARGIN = 0.005
DELTA_MAX_PCT = 2.0

X.EQUITY_PCT = EQUITY_PCT


def http_json(path, params, tries=3, timeout=20):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(FAPI + path + "?" + q,
                                 headers={"User-Agent": "neutral-paper-bot-1m/1.0"})
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


def iso(ms):
    return (datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if ms else None)


# ------------------------------------------------------------------ data
def csv_path(sym):
    return os.path.join(K15, f"{sym}_15m.csv")


def csv_path_1m(sym):
    return os.path.join(K1, f"{sym}_1m.csv")


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
    """Append CLOSED bars only, idempotently (15m decision bars)."""
    os.makedirs(K15, exist_ok=True)
    path = csv_path(sym)
    have = read_ts(path)
    end = int(time.time() * 1000)
    new = []
    st = (max(have) + tfms) if have else None
    MIN_COVER_MS = 90 * 24 * 3600 * 1000
    span = (max(have) - min(have)) if len(have) > 1 else 0
    first = (not have) or (span < MIN_COVER_MS)
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
            if oldest <= 1567296000000:
                break
            back = oldest
            time.sleep(0.12)
        st = None
    while st:
        params = {"symbol": sym, "interval": interval, "limit": 1000, "startTime": st}
        try:
            d = http_json("/fapi/v1/klines", params)
        except Exception as e:
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


def pull_1m(sym, since_ms, max_pages=4000):
    """Append CLOSED 1m klines from `since_ms` forward, idempotently.

    Only CLOSED minutes are written, so a forming minute can never enter the
    tape and a bar cannot flip from partial to resolved mid-cycle.
    """
    os.makedirs(K1, exist_ok=True)
    path = csv_path_1m(sym)
    have = read_ts(path)
    end = int(time.time() * 1000)
    st = (max(have) + ONE_M_MS) if have else since_ms
    new = []
    pages = 0
    capped = False
    while st < end and pages < max_pages:
        params = {"symbol": sym, "interval": "1m", "limit": 1000, "startTime": st}
        try:
            d = http_json("/fapi/v1/klines", params)
        except Exception as e:
            print(f"  {sym}: 1m pull stopped: {type(e).__name__} {str(e)[:80]}", flush=True)
            break
        if not d:
            break
        pages += 1
        for x in d:
            t = int(x[0])
            if t + ONE_M_MS > end:
                continue
            if t not in have:
                new.append((t, x[1], x[2], x[3], x[4], x[5]))
                have.add(t)
        if len(d) < 1000:
            break
        st = int(d[-1][0]) + ONE_M_MS
        time.sleep(0.12)
        if pages >= max_pages and st < end:
            capped = True
    if new:
        new.sort()
        need_hdr = (not os.path.exists(path)) or os.path.getsize(path) == 0
        with open(path, "w" if need_hdr else "a", newline="") as f:
            w = csv.writer(f)
            if need_hdr:
                w.writerow(["open_ts", "open", "high", "low", "close", "volume"])
            w.writerows(new)
    return path, len(new), ("capped" if capped else "ok")


def pull_funding(sym, since_ms):
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
    START_TOL_MS = 24 * 3600 * 1000
    covers = (first <= b0 + START_TOL_MS) and (last >= b1 - FUNDING_INTERVAL_MS)
    return covers, first, last, len(ts)


def save_forward_artifact(status, bars, day0, tr, scale):
    """bt-artifact/1 JSON so the forward record is guard-backed and verifiable."""
    import hashlib
    runs_dir = os.path.join(HOME, "runs")
    os.makedirs(runs_dir, exist_ok=True)
    d0_bar = int(day0["last_bar"])
    fwd_trades = [t_ for t_ in tr["trades"]
                  if int(t_["ts"]) > d0_bar and int(t_.get("entry_ts", 0)) > d0_bar]
    k15_path = csv_path(SYMBOL)
    k1_path = csv_path_1m(SYMBOL)
    fund_path = os.path.join(FUNDDIR, f"{SYMBOL}_funding.json")

    inputs = []
    if os.path.exists(k15_path):
        h = hashlib.sha256(open(k15_path, "rb").read()).hexdigest()
        inputs.append([os.path.abspath(k15_path), h, len(bars)])
    if os.path.exists(k1_path):
        h1 = hashlib.sha256(open(k1_path, "rb").read()).hexdigest()
        inputs.append([os.path.abspath(k1_path), h1, status["one_m"]["tape_rows"]])
    if os.path.exists(fund_path):
        hf = hashlib.sha256(open(fund_path, "rb").read()).hexdigest()
        inputs.append([os.path.abspath(fund_path), hf, status["funding_prints"]])

    eng_path = os.path.join(HERE, "xrp_neutral_engine_paper_1m.py")
    eng_sha = hashlib.sha256(open(eng_path, "rb").read()).hexdigest()
    # The base engine is the file deployed as xrp_neutral_engine.py; its sha is
    # pinned here rather than read, because the pair directories carry only the
    # 15m engine and the generated 1m variant.
    base_sha = BASE_ENGINE_SHA

    core = {
        "strategy": "xrpneutral_forward_1m",
        "params": status["config"],
        "inputs": inputs,
        "engine_sha256": eng_sha,
        "base_engine_sha256": base_sha,
        "engine_version": "xrp-neutral-fwd-1m-1",
    }
    run_id = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]

    art = {
        "schema": "bt-artifact/1",
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "strategy": "xrpneutral_forward_1m",
        "symbol": SYMBOL,
        "timeframe": INTERVAL,
        "fill_timeframe": "1m",
        "params": status["config"],
        "provenance": {
            "adapter": "xrpneutral_forward_1m",
            "engine_version": "xrp-neutral-fwd-1m-1",
            "engine_files": ["xrp_neutral_engine_paper_1m.py",
                             "neutral_paper_1m.py",
                             "xrp_neutral_engine_paper.py"],
            "engine_sha256": eng_sha,
            "base_engine_sha256": base_sha,
            "mode": "forward-paper-live-1m",
            "fill_model": status["fill_model"],
            "day0_utc": day0.get("created_utc"),
            "scale": scale,
            "deployed_bot": {"name": BOT_LABEL, "symbol": SYMBOL, "timeframe": INTERVAL},
        },
        "inputs": [{"path": p[0], "sha256": p[1], "bars": p[2]} for p in inputs],
        "metrics": {
            "return_pct": status["forward_pct"],
            "forward_pnl_usdt": status["forward_pnl"],
            "profit_factor": status["forward_pf"],
            "win_rate": (status["forward_win_rate_pct"] / 100.0
                         if status["forward_win_rate_pct"] is not None else None),
            "n_trades": status["forward_closed_lots"],
            "equity": status["equity"],
            "init_usdt": status["init_usdt"],
            "max_dd_pct": status["max_dd_pct"],
            "max_gross_leverage": status["max_gross_leverage"],
            "min_margin_buffer_pct": status["min_margin_buffer_pct"],
            "NEUTRALITY_avg_abs_delta_pct": status["NEUTRALITY_avg_abs_delta_pct"],
            "kill_triggered": status["kill_triggered"],
            "kill_reason": status["kill_reason"],
            "forward_coverage_pct": status["one_m"]["forward_coverage_pct"],
            "same_minute_touched": status["one_m"]["same_minute_touched"],
            "same_bar_covers": status["one_m"]["same_bar_covers"],
            "one_m_covers": status["one_m"]["one_m_covers"],
            "flag": "OK" if status["forward_closed_lots"] >= 30 else "ACCUMULATING_SAMPLE",
        },
        "tables": [{"ts": t_["ts"], "side": t_["dir"], "qty": t_["qty"],
                    "entry": t_["entry"], "exit": t_["exit"],
                    "pnl": t_["pnl"] * scale, "reason": t_["reason"],
                    "entry_min_ts": t_.get("entry_min_ts"),
                    "exit_min_ts": t_.get("exit_min_ts")}
                   for t_ in fwd_trades],
        "core": core,
        "cmd": f"python neutral_paper_1m.py --once  # {SYMBOL}",
    }
    out_path = os.path.join(runs_dir, f"{run_id}.json")
    latest_path = os.path.join(runs_dir, "forward_latest_1m.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(art, f, indent=2, sort_keys=True)
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(art, f, indent=2, sort_keys=True)
    return out_path, run_id


def one_m_block(tr, bars, day0, n_tape, tape_first, tape_last, day0_check):
    d0_bar = int(day0["last_bar"])
    ix = {int(b[0]): i for i, b in enumerate(bars)}
    i0 = ix.get(d0_bar)
    flags = [bool(x) for x in tr.get("res_flags", [])]
    if i0 is None:
        fwd = flags
    else:
        fwd = flags[i0 + 1:]
    n_fwd = len(fwd)
    n_res = int(sum(1 for x in fwd if x))
    fwd_trades = [t_ for t_ in tr["trades"]
                  if int(t_["ts"]) > d0_bar and int(t_.get("entry_ts", 0)) > d0_bar]
    # A same-bar cover is a FABRICATION only when both fills came from the
    # fallback model on the same bar. A cover on a resolved bar carries a real
    # exit minute even though its 15m bar timestamp equals the entry's.
    fwd_same_bar = sum(1 for t_ in fwd_trades
                       if t_["reason"] == "cover"
                       and int(t_.get("entry_min_ts", -1)) == -1
                       and int(t_.get("exit_min_ts", -1)) == -1
                       and int(t_.get("entry_ts", 0)) == int(t_["ts"]))
    fwd_1m = sum(1 for t_ in fwd_trades
                 if t_["reason"] == "cover"
                 and int(t_.get("exit_min_ts", -1)) >= 0)
    return {
        "fill_model": "1m_resolved_on_complete_tape; same-bar fallback otherwise",
        "tape_rows": int(n_tape),
        "tape_first_utc": iso(tape_first),
        "tape_last_utc": iso(tape_last),
        "minutes_used": int(tr["minutes_used"]),
        "bars_resolved": int(tr["bars_resolved"]),
        "bars_partial": int(tr["bars_partial"]),
        "bars_no_tape": int(tr["bars_no_tape"]),
        "forward_bars": n_fwd,
        "forward_bars_resolved": n_res,
        "forward_bars_not_resolved": n_fwd - n_res,
        "forward_coverage_pct": round(100.0 * n_res / max(n_fwd, 1), 2),
        "forward_coverage_ok": bool(n_fwd > 0 and n_res == n_fwd),
        "day0_replay_matches": (None if day0_check is None
                                else bool(day0_check.get("matches"))),
        "day0_prefix_engine_eq": (None if day0_check is None
                                  else day0_check.get("prefix_engine_eq")),
        "tape_isolated": bool(n_tape and tape_first >= d0_bar + TF_MS),
        "same_minute_touched": int(tr["same_minute_touched"]),
        "same_bar_covers": int(tr["same_bar_covers"]),
        "one_m_covers": int(tr["one_m_covers"]),
        "forward_same_bar_covers": int(fwd_same_bar),
        "forward_one_m_covers": int(fwd_1m),
        "res_first_utc": iso(int(tr.get("res_first_ts") or 0)),
        "res_last_utc": iso(int(tr.get("res_last_ts") or 0)),
    }


def day0_prefix_check(bars, day0, i0, write=True):
    """Exact check that the day-0 baseline is still the 15m engine's number.

    The dual engine is bit-identical to the 15m engine on every bar before the
    tape begins, so running the PURE 15m path on the prefix [0..i0] must
    reproduce the frozen mtm_engine bit-for-bit. Computed once and cached,
    keyed by (day-0 bar, prefix length, engine sha): a changed history or a
    rebuilt engine forces a recompute. A FALSE here means the baseline moved
    and the forward numbers are not comparable with the 15m record.
    """
    eng_sha = hashlib.sha256(open(ENGINE_FILE, "rb").read()).hexdigest()
    cached = load_json(DAY0_CHECK)
    if (cached.get("day0_bar") == int(day0["last_bar"])
            and cached.get("engine_sha256") == eng_sha
            and cached.get("bars") == i0 + 1):
        return cached
    saved = os.environ.pop("NP_1M_CSV", None)
    try:
        tr0 = {}
        eq0 = X.simulate(bars[:i0 + 1], SYMBOL, funding=True, fund_dir=FUNDDIR,
                         init=INIT_USDT, delta_max_pct=DELTA_MAX_PCT,
                         track=tr0, **CONFIG)
    finally:
        if saved is not None:
            os.environ["NP_1M_CSV"] = saved
    chk = {"day0_bar": int(day0["last_bar"]), "bars": i0 + 1,
           "engine_sha256": eng_sha,
           "day0_mtm_engine": float(day0["mtm_engine"]),
           "prefix_engine_eq": float(eq0),
           "matches": bool(abs(float(eq0) - float(day0["mtm_engine"])) < 1e-9),
           "checked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if write:
        json.dump(chk, open(DAY0_CHECK, "w"), indent=1)
    return chk


def load_json(path):
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            return {}
    return {}


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="run one cycle")
    ap.add_argument("--init", action="store_true",
                    help="freeze day-0 from the 15m engine if it does not exist")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="read local files only: no fetch, no writes")
    a = ap.parse_args()

    if a.status:
        print(open(STATUS, encoding="utf-8").read() if os.path.exists(STATUS)
              else "no 1m status yet")
        return

    day0 = load_json(DAY0)
    if not day0:
        if not a.init:
            print(f"  day-0 missing at {DAY0}: the 15m bot owns the baseline; "
                  f"run the 15m cycle first (or --init once)")
            return
        import xrp_neutral_engine as B
        B.EQUITY_PCT = EQUITY_PCT
        path, _, _ = pull_klines(SYMBOL, INTERVAL, TF_MS)
        pull_funding(SYMBOL, FUNDING_FLOOR_MS)
        bars = load_bars(path)
        tr0 = {}
        eq0 = B.simulate(bars, SYMBOL, funding=True, fund_dir=FUNDDIR, init=INIT_USDT,
                         delta_max_pct=DELTA_MAX_PCT, track=tr0, **CONFIG)
        d0 = {"created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "sym": SYMBOL, "config": CONFIG, "delta_max_pct": DELTA_MAX_PCT,
              "sizing": {"init_usdt": INIT_USDT, "equity_pct": EQUITY_PCT,
                         "leverage": LEVERAGE},
              "mtm_engine": float(eq0), "scale": INIT_USDT / float(eq0),
              "mtm": INIT_USDT, "fees_engine": float(tr0["fees"]),
              "fund_engine": float(tr0["fund"]), "last_bar": int(bars[-1][0]),
              "open_lots": int(tr0["open_lots"]),
              "n_closed": len(tr0["closed_pnl"]),
              "frozen_by": "neutral_paper_1m.py --init (15m engine)"}
        json.dump(d0, open(DAY0, "w"), indent=1)
        print(f"day-0 frozen at {iso(d0['last_bar'])}: engine ${eq0:,.2f} -> "
              f"{INIT_USDT:.2f} account")
        return

    d0_bar = int(day0["last_bar"])
    tape_start = d0_bar + TF_MS

    if a.dry_run:
        path = csv_path(SYMBOL)
        p1 = csv_path_1m(SYMBOL)
        if not os.path.exists(p1):
            print(f"  dry-run: no 1m tape at {p1}")
            return
        bars = load_bars(path)
        n_new = 0
        n_tape = len(read_ts(p1))
    else:
        os.makedirs(HOME, exist_ok=True)
        path, n_new, note = pull_klines(SYMBOL, INTERVAL, TF_MS)
        if note != "ok":
            print(f"  kline pull failed: {note}")
            return
        n_fund, note_f = pull_funding(SYMBOL, FUNDING_FLOOR_MS)
        if note_f != "ok":
            print(f"  funding pull failed: {note_f}")
        p1, n_1m_new, note_1m = pull_1m(SYMBOL, tape_start)
        if note_1m != "ok":
            print(f"  1m pull note: {note_1m}")
        bars = load_bars(path)
        n_tape = len(read_ts(p1))

    if len(bars) < 2000:
        print(f"  only {len(bars)} bars, not enough to run")
        return

    covers, f_first, f_last, f_n = funding_coverage(bars, FUNDDIR)
    if not covers:
        print(f"  WARNING: funding history does NOT cover the bar range "
              f"(prints {f_n}, {iso(f_first)} -> {iso(f_last)} vs bars "
              f"{iso(bars[0][0])} -> {iso(bars[-1][0])})", flush=True)

    # The tape must never reach back to the day-0 bar: that bar keeps the 15m
    # convention so the baseline equity cannot move.
    tape_first = min(read_ts(p1)) if n_tape else 0
    tape_last = max(read_ts(p1)) if n_tape else 0
    if n_tape and tape_first < tape_start:
        print(f"  WARNING: 1m tape starts at {iso(tape_first)}, BEFORE the bar after "
              f"day-0 ({iso(tape_start)}); the day-0 baseline may have moved. "
              f"XRP_BOT_DATA should start from a fresh day-0.", flush=True)

    os.environ["NP_1M_CSV"] = p1 if n_tape else ""
    tr = {}
    eq = X.simulate(bars, SYMBOL, funding=True, fund_dir=FUNDDIR, init=INIT_USDT,
                    delta_max_pct=DELTA_MAX_PCT, track=tr, **CONFIG)
    os.environ.pop("NP_1M_CSV", None)

    ix0 = {int(b[0]): i for i, b in enumerate(bars)}.get(d0_bar)
    day0_check = (day0_prefix_check(bars, day0, ix0, write=not a.dry_run)
                  if ix0 is not None else None)

    cp = tr["closed_pnl"]
    pf, win, n_closed = X.metrics(cp)
    gross = sum(abs(x) for x in cp) or 1.0
    eqc = tr["eq_curve"]
    d = tr["delta_curve"]
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.abs(d) / np.where(eqc > 0, eqc, np.nan)
    last_bar = int(bars[-1][0])
    gate_now = float(X.trend_strength(bars)[-1])

    _stops = [int(t_["ts"]) for t_ in tr["trades"] if t_["reason"] == "stop"]
    last_stop = max(_stops) if _stops else 0
    cooldown_until = last_stop + 96 * TF_MS if last_stop else 0
    cooldown_left = (max(0, int((cooldown_until - last_bar + TF_MS - 1) // TF_MS))
                     if last_stop else 0)

    scale = float(day0["scale"])
    eq_acct = float(eq) * scale
    fwd = (float(eq) - float(day0["mtm_engine"])) * scale
    fwd_pct = 100 * (float(eq) / max(float(day0["mtm_engine"]), 1e-9) - 1)
    fees_acct = (float(tr["fees"]) - float(day0.get("fees_engine", 0.0))) * scale
    fund_acct = (float(tr["fund"]) - float(day0.get("fund_engine", 0.0))) * scale

    fwd_trades = [t_ for t_ in tr["trades"]
                  if int(t_["ts"]) > d0_bar and int(t_.get("entry_ts", 0)) > d0_bar]
    if fwd_trades:
        fwd_pf, fwd_win, fwd_n = X.metrics([t_["pnl"] for t_ in fwd_trades])
        fwd_closed = float(sum(t_["pnl"] for t_ in fwd_trades)) * scale
    else:
        fwd_pf, fwd_win, fwd_n, fwd_closed = None, None, 0, 0.0
    if fwd_pf is not None and not np.isfinite(fwd_pf):
        fwd_pf = None

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

    # append-only event log; the key carries the minute metadata so a trade
    # that gains 1m resolution later is not silently dropped.
    new_rows = []
    if os.path.exists(EVENTS):
        with open(EVENTS) as f:
            seen = {(r["ts"], r["side"], r["entry"], r["exit"], r["pnl"],
                     r.get("entry_min_ts"), r.get("exit_min_ts"))
                    for r in csv.DictReader(f)}
    else:
        seen = set()
    for t_ in fwd_trades:
        key = (str(t_["ts"]), str(t_["dir"]), f"{t_['entry']:.8f}",
               f"{t_['exit']:.8f}", f"{t_['pnl']:.6f}",
               str(t_.get("entry_min_ts")), str(t_.get("exit_min_ts")))
        if key in seen:
            continue
        seen.add(key)
        new_rows.append([t_["ts"], t_["entry_ts"], t_.get("entry_min_ts"),
                         t_.get("exit_min_ts"), t_["dir"], f"{t_['qty']:.6f}",
                         f"{t_['entry']:.8f}", f"{t_['exit']:.8f}",
                         f"{t_['pnl']:.6f}", t_["reason"]])
    if new_rows and not a.dry_run:
        need = (not os.path.exists(EVENTS)) or os.path.getsize(EVENTS) == 0
        with open(EVENTS, "a", newline="") as f:
            w = csv.writer(f)
            if need:
                w.writerow(["ts", "entry_ts", "entry_min_ts", "exit_min_ts",
                            "side", "qty", "entry", "exit", "pnl", "reason"])
            w.writerows(new_rows)

    s15 = load_json(STATUS_15)
    vs15 = None
    if s15:
        vs15 = {
            "status_file": os.path.basename(STATUS_15),
            "updated_utc": s15.get("updated_utc"),
            "last_bar": s15.get("last_bar"),
            "same_last_bar": bool(s15.get("last_bar") == iso(last_bar)),
            "equity": s15.get("equity"),
            "forward_pnl": s15.get("forward_pnl"),
            "forward_pf": s15.get("forward_pf"),
            "forward_closed_lots": s15.get("forward_closed_lots"),
            "equity_delta_1m_minus_15m": (round(eq_acct - float(s15["equity"]), 4)
                                          if s15.get("equity") is not None else None),
            "forward_pnl_delta_1m_minus_15m": (
                round(fwd - float(s15["forward_pnl"]), 4)
                if s15.get("forward_pnl") is not None else None),
        }

    status = {
        "bot": BOT_LABEL,
        "updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "PAPER - no orders are placed, no keys are read, Binance public REST only",
        "fill_model": "1m_resolved_on_complete_tape",
        "sym": SYMBOL, "tf": INTERVAL, "config": CONFIG,
        "trend_band": CONFIG["trend_band"],
        "trend_strength_pct": round(gate_now * 100, 3),
        "trend_gate_on": bool(gate_now <= CONFIG["trend_band"]),
        "delta_max_pct": DELTA_MAX_PCT,
        "sizing": {"init_usdt": INIT_USDT, "equity_pct": EQUITY_PCT,
                   "leverage": LEVERAGE},
        "account_note": "USDT fields are normalised to an INIT_USDT day-0 account; "
                        "engine_equity is the raw compounded replay scale",
        "last_bar": iso(last_bar), "new_15m_bars": int(n_new),
        "new_1m_bars": int(0 if a.dry_run else n_1m_new),
        "funding_prints": int(f_n),
        "last_stop_utc": iso(last_stop),
        "cooldown_until_utc": iso(cooldown_until) if last_stop else None,
        "cooldown_bars_left": int(cooldown_left),
        "bars": len(bars),
        "equity": round(eq_acct, 2),
        "init_usdt": INIT_USDT,
        "net_from_inception_pct": round(fwd_pct, 3),
        "forward_pnl": round(fwd, 2), "forward_pct": round(fwd_pct, 3),
        "forward_closed_lots": int(fwd_n),
        "forward_closed_pnl": round(fwd_closed, 4),
        "forward_carry_pnl": round(fwd - fwd_closed, 4),
        "forward_trade_basis": "lots opened AND closed after day-0; carry lots "
                               "opened before day-0 move equity but are excluded",
        "day0_open_lots": int(day0.get("open_lots", 0)),
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
        "funding_first_print": iso(f_first),
        "funding_last_print": iso(f_last),
        "open_lots": int(tr["open_lots"]),
        "grids_built": int(tr["grids"]), "fills": int(tr["fills"]),
        "cycles": int(tr["cycles"]),
        "NEUTRALITY_avg_abs_delta_pct": round(float(np.nanmean(ratio) * 100), 3),
        "NEUTRALITY_max_abs_delta_pct": round(float(np.nanmax(ratio) * 100), 3),
        "delta_cap_hits": int(tr["delta_cap_hits"]),
        "trend_standdown_bars": int(tr["stand_down_bars"]),
        "max_gross_leverage": round(float(np.max(tr["expo_curve"])), 2),
        "min_margin_buffer_pct": round(float(np.min(
            (eqc - MAINT_MARGIN * np.asarray(tr["gross_curve"], float))
            / np.maximum(eqc, 1e-12)) * 100.0), 1),
        "exit_reasons": tr["reasons"],
        "buyhold_pct": round(100 * (bars[-1][4] / bars[0][4] - 1), 1),
        "new_trades_logged": len(new_rows),
        "one_m": one_m_block(tr, bars, day0, n_tape, tape_first, tape_last,
                             day0_check),
        "vs_15m": vs15,
    }

    if a.dry_run:
        status["dry_run"] = True
        print(json.dumps(status, indent=1, default=str), flush=True)
        return

    art_path, art_id = save_forward_artifact(status, bars, day0, tr, scale)
    status["forward_artifact"] = art_path
    status["forward_run_id"] = art_id
    json.dump(status, open(STATUS, "w"), indent=1)
    print(json.dumps(status, indent=1), flush=True)


if __name__ == "__main__":
    main()
