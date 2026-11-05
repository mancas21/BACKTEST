"""Forward paper mirror — CVRMD-SUI 1H + BOT-ETH 1H on VPS cron (*/5).
Design: NO separate fill simulator. Each cycle pulls only CLOSED bars via
Binance REST, appends idempotently to local CSVs, and re-runs the validated
batch engines on full history. Paper equity = engine equity; open positions
are the engine's own state. Recognition lag <= 1 cycle; numbers identical to
a backtest on the same data by construction.
Day 0: legs start mirroring as-is. Positions already open at Day 0 are flagged
HELD_PRE (entered before paper start); forward P&L measured from Day-0 MTM
snapshot, so pre-existing unrealized never counts as paper performance.
Out of scope (documented kills/suspensions, NOT papered):
  FFS-v1 HYPE 5m — KILLED 2026-10-01 (full PF 0.93, halves 0.95/0.91).
  CVRMD-ETH 1H — SUSPENDED (validated window +11.1%/1.70 reproduces exactly,
  but full 2019+ history PF 1.02: flat; needs regime explanation first).
Usage: python paper_live.py   (cron: */5 * * * * cd ~/paper && python3 paper_live.py)
Outputs: paper_trades.csv (new log events), status.json, day0.json.
"""
import sys
import os
import csv
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "code"))
DATA = os.path.join(HERE, "data")
FAPI = "https://fapi.binance.com"

LEG_DEFS = [
    dict(leg="CVRMD-SUI-1H", engine="cvrmd", sym="SUIUSDT", tf="1h", tfms=3600000),
    dict(leg="BOT-ETH-1H", engine="bot", sym="ETHUSDT", tf="1h", tfms=3600000),
]

TRADES_CSV = os.path.join(HERE, "paper_trades.csv")
STATUS_JSON = os.path.join(HERE, "status.json")
DAY0_JSON = os.path.join(HERE, "day0.json")


def http_json(url, params):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(url + "?" + q, headers={"User-Agent": "paper/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def csv_path(sym, tf):
    return os.path.join(DATA, "binance_klines_1h", sym + "_" + tf + ".csv")


def read_ts(path):
    have = {}
    if os.path.exists(path):
        with open(path) as f:
            for row in csv.DictReader(f):
                try:
                    have[int(row["open_ts"])] = True
                except (ValueError, KeyError):
                    pass
    return have


def pull(sym, tf, tfms):
    path = csv_path(sym, tf)
    have = read_ts(path)
    interval = "1h"
    if have:
        start = max(have) + tfms
    else:
        start = None  # full bootstrap
    new = []
    end = int(time.time() * 1000)
    if start is None:
        st = 0
        first = True
    else:
        st = start
        first = False
    while True:
        params = {"symbol": sym, "interval": interval, "limit": 1000}
        if st:
            params["startTime"] = st
        try:
            d = http_json(FAPI + "/fapi/v1/klines", params)
        except Exception as e:
            return path, 0, "REST_ERR " + str(e)[:100]
        if not d:
            break
        for x in d:
            t = int(x[0])
            if t + tfms > end:
                continue  # forming bar: never touch
            if t not in have:
                new.append((t, x[1], x[2], x[3], x[4], x[5]))
                have[t] = True
        if len(d) < 1000:
            break
        st = d[-1][0] + 1
        time.sleep(0.2)
    if new:
        new.sort()
        mode = "a" if (first and os.path.exists(path)) or have else "w"
        need_hdr = (not os.path.exists(path)) or os.path.getsize(path) == 0
        if need_hdr:
            mode = "w"
        with open(path, mode, newline="") as f:
            w = csv.writer(f)
            if need_hdr:
                w.writerow(["open_ts", "open", "high", "low", "close", "volume"])
            for r in new:
                w.writerow(r)
    return path, len(new), "ok"


def load_bars(path):
    bars = []
    with open(path) as f:
        for row in csv.DictReader(f):
            bars.append((int(row["open_ts"]), float(row["open"]), float(row["high"]),
                         float(row["low"]), float(row["close"]), float(row["volume"])))
    bars.sort(key=lambda b: b[0])
    return bars


def mtm_cvrmd(eq, st, last_close):
    if st["pos"] != 0 and st["ep"]:
        pr = (last_close - st["ep"]) / st["ep"] if st["pos"] == 1 else (st["ep"] - last_close) / st["ep"]
        return max(eq * (1 + st["qty"] * pr), 0.0)
    return eq


def mtm_bot(eq, st, last_close):
    if st["pos"] != 0 and st["ep"]:
        pr = (last_close - st["ep"]) / st["ep"] if st["pos"] == 1 else (st["ep"] - last_close) / st["ep"]
        return max(eq * (1 + st["rem"] * pr), 0.0)
    return eq


def main():
    import cvrmd_backtest as C
    import botstrat_backtest as B
    seen = set()
    if os.path.exists(TRADES_CSV):
        with open(TRADES_CSV) as f:
            for row in csv.DictReader(f):
                seen.add((row["leg"], row["ts"], row["ret"]))
    day0 = {}
    if os.path.exists(DAY0_JSON):
        day0 = json.load(open(DAY0_JSON))
    status = {"updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "legs": []}
    new_trades = []
    for ld in LEG_DEFS:
        path, added, note = pull(ld["sym"], ld["tf"], ld["tfms"])
        if note != "ok":
            status["legs"].append(dict(leg=ld["leg"], error=note))
            continue
        bars = load_bars(path)
        if ld["engine"] == "cvrmd":
            eq, tr_, w_, gp, gl, mdd, logs, st = C.run(ld["sym"], bars, return_state=True)
            mtm = mtm_cvrmd(eq, st, bars[-1][4])
            pf = gp / gl if gl > 0 else 0.0
        else:
            eq, tr_, w_, gp, gl, mdd, logs, closes, st = B.run(ld["sym"], bars, return_state=True)
            mtm = mtm_bot(eq, st, bars[-1][4])
            pf = gp / gl if gl > 0 else 0.0
            logs = [(t, r) for t, r in logs]
        for t, r in logs:
            key = (ld["leg"], str(t), repr(r))
            if key not in seen:
                seen.add(key)
                new_trades.append((ld["leg"], t, r))
        if ld["leg"] not in day0:
            day0[ld["leg"]] = {"mtm": float(mtm), "ts": int(st["last_ts"]),
                               "held_pre": bool(st["pos"] != 0)}
        if st["pos"] == 0 and day0[ld["leg"]].get("held_pre"):
            day0[ld["leg"]]["held_pre"] = False
        pre_ex = bool(st["pos"] != 0 and day0[ld["leg"]].get("held_pre"))
        fwd = mtm - day0[ld["leg"]]["mtm"]
        iso = datetime.fromtimestamp(st["last_ts"] / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        status["legs"].append(dict(
            leg=ld["leg"], last_bar=iso, added_bars=int(added),
            pos=int(st["pos"]), ep=round(float(st["ep"]), 6) if st["ep"] else 0.0,
            realized_eq=round(float(eq), 2), mtm_eq=round(float(mtm), 2),
            fwd_net=round(float(fwd), 2),
            fwd_pct=round((float(fwd) / day0[ld["leg"]]["mtm"]) * 100, 3),
            n_logs=int(len(logs)), pf=round(float(pf), 3),
            pre_existing=pre_ex,
        ))
    for ld in LEG_DEFS:
        if ld["leg"] in day0:
            day0[ld["leg"]]["synced"] = True
    json.dump(day0, open(DAY0_JSON, "w"), indent=1)
    if new_trades:
        need_hdr = (not os.path.exists(TRADES_CSV)) or os.path.getsize(TRADES_CSV) == 0
        with open(TRADES_CSV, "a", newline="") as f:
            w = csv.writer(f)
            if need_hdr:
                w.writerow(["leg", "ts", "ret"])
            for leg, t, r in sorted(new_trades, key=lambda x: (x[0], x[1])):
                w.writerow([leg, t, repr(r)])
    json.dump(status, open(STATUS_JSON, "w"), indent=1)
    print(json.dumps(status, indent=1), flush=True)


if __name__ == "__main__":
    main()
