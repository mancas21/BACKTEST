"""Neutral futures-grid backtest on Binance USDT-M 5m OHLC.
Follows grid-backtest skill (conservative sweep, taker fees per fill,
net-equity DD, halt on breach, range-hold + neighborhood) and
quant-research (IS-calibrated range, embargoed OOS, no lookahead).
"""
import os, csv, json, math

DATA = r"C:\Users\Lenovo\AppData\Local\Temp\opencode\binance_klines"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "SUIUSDT"]
INTERVAL = "5m"
INVEST = 100.0
LEV = 3.0
ROW = 20
TAKER = 0.0005  # conservative: OHLC sweep assumes taker fills
IS_BARS = 7 * 288  # 7 days of 5m
EMBARGO = 12       # 1h purge around split boundary

def load(symbol):
    path = os.path.join(DATA, f"{symbol}_{INTERVAL}.csv")
    bars = []
    with open(path) as f:
        r = csv.DictReader(f)
        for row in r:
            bars.append({
                "ts": int(row["open_ts"]),
                "o": float(row["open"]), "h": float(row["high"]),
                "l": float(row["low"]), "c": float(row["close"]),
            })
    bars.sort(key=lambda b: b["ts"])  # chronological via int(ts)
    return bars

def build_levels(lower, upper, n, gtype="arithmetic"):
    if gtype == "geometric":
        lo, hi = lower, upper
        ratio = (hi / lo) ** (1.0 / n)
        return [lo * (ratio ** i) for i in range(n + 1)]
    step = (upper - lower) / n
    return [lower + step * i for i in range(n + 1)]

def cell_index(price, levels):
    # index of cell containing price; clamp
    if price <= levels[0]:
        return -1
    if price >= levels[-1]:
        return len(levels) - 1
    for i in range(len(levels) - 1):
        if levels[i] <= price < levels[i + 1]:
            return i
    return len(levels) - 2

def run_grid(bars, lower, upper, n=ROW, gtype="arithmetic", fee_rate=TAKER, lev=LEV):
    levels = build_levels(lower, upper, n, gtype)
    # notional per grid cell: investment*leverage / cells (neutral: all cells)
    notional = INVEST * lev / n
    cash = 0.0
    inv = 0.0  # base inventory (+long/-short)
    fills = 0
    fees = 0.0
    closed_pnls = []  # round-trip proxy: match FIFO lots
    lots = []  # (side, qty, price) open lots; side +1 long/-1 short
    gross_profit = 0.0
    gross_loss = 0.0

    def match_fill(side, qty, price):
        """FIFO match against opposite open lots; book closed P&L net of approximated fees."""
        nonlocal lots, gross_profit, gross_loss
        need = qty
        while need > 1e-12 and lots and lots[0][0] == -side:
            s, q, p = lots[0]
            take = min(need, q)
            # new buy (+1) closes prior short (-1): profit = short_price - buy_price
            # new sell (-1) closes prior long (+1): profit = sell_price - buy_price
            if side == +1:
                pnl = take * (p - price)
            else:
                pnl = take * (price - p)
            if pnl >= 0:
                gross_profit += pnl
            else:
                gross_loss += -pnl
            if take >= q - 1e-12:
                lots.pop(0)
            else:
                lots[0] = (s, q - take, p)
            need -= take
        if need > 1e-12:
            lots.append((side, need, price))
    eq_curve = []
    peak = -1e18
    max_dd = 0.0
    in_range_bars = 0
    halted = False
    halt_ts = None
    prev_cell = None
    # init at first OOS open
    prev_cell = cell_index(bars[0]["o"], levels)

    for b in bars:
        o, h, l, c = b["o"], b["h"], b["l"], b["c"]
        # breach check on bar extremes -> halt, liquidate, stop
        if h > upper or l < lower:
            # liquidate inventory at breach edge with taker fee:
            # close long (+inv): sell -> cash += inv*px - fee
            # close short (-inv): buy back -> cash += inv*px - fee (inv<0 subtracts)
            px = upper if h > upper else lower
            if abs(inv) > 1e-12:
                fee = abs(inv) * px * fee_rate
                fees += fee
                cash += inv * px - fee
                inv = 0.0
                lots = []
            fills += 0
            eq = cash
            eq_curve.append(eq)
            peak = max(peak, eq)
            max_dd = max(max_dd, peak - eq)
            halted = True
            halt_ts = b["ts"]
            break
        in_range_bars += 1
        bull = c >= o
        path = [o, l, h, c] if bull else [o, h, l, c]
        # conservative sweep o->l->h->c / o->h->l->c
        for p in path[1:]:
            ci = cell_index(p, levels)
            if prev_cell is None:
                prev_cell = ci
                continue
            # only act when inside grid
            if ci < 0 or ci > n - 1 or prev_cell < 0 or prev_cell > n - 1:
                prev_cell = ci
                continue
            d = ci - prev_cell
            if d > 0:
                # price moved up through d levels -> d sells
                for k in range(d):
                    lvl = levels[prev_cell + 1 + k]
                    qty = notional / lvl
                    fee = qty * lvl * fee_rate
                    fees += fee
                    cash += qty * lvl - fee
                    inv -= qty
                    match_fill(-1, qty, lvl)
                    fills += 1
            elif d < 0:
                for k in range(-d):
                    lvl = levels[prev_cell - k]
                    qty = notional / lvl
                    fee = qty * lvl * fee_rate
                    fees += fee
                    cash += -qty * lvl - fee
                    inv += qty
                    match_fill(+1, qty, lvl)
                    fills += 1
            prev_cell = ci
        # net equity MTM at close
        eq = cash + inv * c
        eq_curve.append(eq)
        peak = max(peak, eq)
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd

    last = bars[len(eq_curve) - 1]["c"] if eq_curve else bars[-1]["c"]
    net = (eq_curve[-1] if eq_curve else 0.0)
    pf = (gross_profit / gross_loss) if gross_loss > 1e-9 else None
    return {
        "lower": lower, "upper": upper, "n": n, "gtype": gtype,
        "fills": fills, "fees": round(fees, 4),
        "gross_profit": round(gross_profit, 4), "gross_loss": round(gross_loss, 4),
        "profit_factor": round(pf, 4) if pf is not None else None,
        "net": round(net, 4), "net_pct_invest": round(net / INVEST * 100, 3),
        "max_dd": round(max_dd, 4),
        "bars": len(bars), "evaluated": len(eq_curve),
        "bars_in_range_pct": round(in_range_bars / len(bars) * 100, 2),
        "halted": halted, "halt_ts": halt_ts,
        "notional_per_cell": round(notional, 4),
    }

out = {}
for sym in SYMBOLS:
    bars = load(sym)
    assert len(bars) >= IS_BARS + EMBARGO + 100, f"{sym} short {len(bars)}"
    is_bars = bars[:IS_BARS]
    oos = bars[IS_BARS + EMBARGO:]
    # IS-calibrated range (no lookahead into OOS)
    lo = min(b["l"] for b in is_bars)
    hi = max(b["h"] for b in is_bars)
    mid_sqrt = math.sqrt(lo * hi)
    mid_arith = (lo + hi) / 2
    base = run_grid(oos, lo, hi, ROW, "arithmetic")
    # neighborhood: width x0.9 / x1.1 around arithmetic mid
    w = hi - lo
    variants = {}
    for f in (0.9, 1.1):
        nlo = mid_arith - w * f / 2
        nhi = mid_arith + w * f / 2
        if nlo <= 0:
            continue
        variants[f"w{f}"] = run_grid(oos, nlo, nhi, ROW, "arithmetic")
    out[sym] = {
        "window_ts": [bars[0]["ts"], bars[-1]["ts"]],
        "n_total": len(bars), "n_is": len(is_bars), "n_oos": len(oos),
        "is_lo": lo, "is_hi": hi,
        "geo_mid_sqrt": mid_sqrt, "arith_mid": mid_arith,
        "base": base, "variants": variants,
    }
    b = base
    print(f"{sym} OOS={len(oos)} range_ok={b['bars_in_range_pct']}% fills={b['fills']} "
          f"net={b['net']} ({b['net_pct_invest']}%) PF={b['profit_factor']} "
          f"fees={b['fees']} dd={b['max_dd']} halted={b['halted']}")

with open(os.path.join(DATA, "grid_report.json"), "w") as f:
    json.dump(out, f, indent=1)
print("wrote grid_report.json")

# ---- Phase 2: walk-forward, trailing-7d calibration, dual fee tiers ----
# Each test week uses ONLY the prior 7d high/low (no lookahead), 12-bar embargo.
MAKER = 0.0002
W = 7 * 288
wf = {}
for sym in SYMBOLS:
    bars = load(sym)
    n = len(bars)
    cum = {TAKER: 0.0, MAKER: 0.0}
    agg = {TAKER: {"fills": 0, "fees": 0.0, "gp": 0.0, "gl": 0.0, "in_range": 0, "tot": 0, "halts": 0},
           MAKER: {"fills": 0, "fees": 0.0, "gp": 0.0, "gl": 0.0, "in_range": 0, "tot": 0, "halts": 0}}
    starts = list(range(0, n - W - EMBARGO - 500, W))
    for s_idx in starts:
        cal = bars[s_idx:s_idx + W]
        tst = bars[s_idx + W + EMBARGO:s_idx + 2 * W + EMBARGO]
        if len(tst) < 500:
            continue
        lo = min(b["l"] for b in cal)
        hi = max(b["h"] for b in cal)
        if hi <= lo:
            continue
        for f in (TAKER, MAKER):
            r = run_grid(tst, lo, hi, ROW, "arithmetic", f)
            a = agg[f]
            a["fills"] += r["fills"]
            a["fees"] += r["fees"]
            a["gp"] += r["gross_profit"]
            a["gl"] += r["gross_loss"]
            a["in_range"] += int(round(r["bars_in_range_pct"] / 100 * r["bars"]))
            a["tot"] += r["bars"]
            a["halts"] += 1 if r["halted"] else 0
            cum[f] += r["net"]
    wf[sym] = {}
    for f, lbl in ((TAKER, "taker05"), (MAKER, "maker02")):
        a = agg[f]
        pf = a["gp"] / a["gl"] if a["gl"] > 1e-9 else None
        wf[sym][lbl] = {
            "windows": len(starts), "fills": a["fills"],
            "fees": round(a["fees"], 2), "net": round(cum[f], 2),
            "net_pct": round(cum[f] / INVEST * 100, 2),
            "PF": round(pf, 4) if pf else None,
            "range_hold_pct": round(a["in_range"] / max(a["tot"], 1) * 100, 1),
            "halts": a["halts"],
        }
    print(f"WF {sym}: taker net={wf[sym]['taker05']['net']} PF={wf[sym]['taker05']['PF']} "
          f"fills={wf[sym]['taker05']['fills']} hold={wf[sym]['taker05']['range_hold_pct']}% | "
          f"maker net={wf[sym]['maker02']['net']} PF={wf[sym]['maker02']['PF']} "
          f"fees={wf[sym]['maker02']['fees']}")

with open(os.path.join(DATA, "grid_report_wf.json"), "w") as f:
    json.dump(wf, f, indent=1)
print("wrote grid_report_wf.json")
