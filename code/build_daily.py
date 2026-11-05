#!/usr/bin/env python3
"""Memory-efficient daily feature builder for rest-mode.
Processes one symbol-day at a time to avoid OOM on low-RAM VPS."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np, pandas as pd

def read_jsonl(path):
    if not path.exists(): return
    with path.open(encoding="utf-8") as f:
        for line in f:
            try: yield json.loads(line)
            except json.JSONDecodeError: continue

def impact_bps(book, quote_notional, side, levels=10):
    if not book: return np.nan
    levels_data = book["asks"] if side == "buy" else book["bids"]
    remain = float(quote_notional); qty = 0.0; cost = 0.0
    for p, q in levels_data[:levels]:
        take = min(float(q), remain / float(p))
        if take <= 0: break
        qty += take; cost += take * float(p); remain -= take * float(p)
        if remain <= 1e-9: break
    if qty <= 0 or remain > 1e-6: return np.nan
    mid = (book["bids"][0][0] + book["asks"][0][0]) / 2.0
    avg = cost / qty
    return ((avg / mid) - 1.0) * 10000.0 if side == "buy" else ((mid / avg) - 1.0) * 10000.0

def book_metrics(bids, asks, levels=5):
    if not bids or not asks: return None
    bs = sorted(bids.items(), reverse=True)[:levels]
    ass = sorted(asks.items())[:levels]
    if not bs or not ass: return None
    bb, bq = bs[0]; ba, aq = ass[0]
    mid = (bb + ba) / 2.0
    spread = (ba - bb) / mid * 10000.0 if mid else np.nan
    bd = sum(q for _, q in bs); ad = sum(q for _, q in ass)
    imb = (bd - ad) / (bd + ad) if (bd + ad) else np.nan
    micro = (ba * bq + bb * aq) / (bq + aq) if (bq + aq) else mid
    edge = (micro - mid) / mid * 10000.0 if mid else np.nan
    return dict(mid=mid, spread_bps=spread, imbalance=imb, micro_edge_bps=edge,
                bid_depth=bd, ask_depth=ad, bid1_qty=bq, ask1_qty=aq,
                buy_impact_bps=impact_bps({"bids":bs,"asks":ass}, 10000.0, "buy", 10),
                sell_impact_bps=impact_bps({"bids":bs,"asks":ass}, 10000.0, "sell", 10))

def rolling_z(s, window=96, minp=24):
    mu = s.rolling(window, min_periods=minp).mean()
    sd = s.rolling(window, min_periods=minp).std(ddof=0)
    return (s - mu) / sd.replace(0, np.nan)

def build_day(root: Path, symbol: str, day_str: str, levels: int):
    d = root / symbol
    trades_path = d / f"{day_str}.trades.jsonl"
    ckpt_path = d / f"{day_str}.depth_checkpoints.jsonl"
    mark_path = d / f"{day_str}.mark_price.jsonl"
    oi_path = d / f"{day_str}.open_interest.jsonl"
    fund_path = d / f"{day_str}.funding.jsonl"
    if not trades_path.exists(): return None

    # Aggregate trades by 5-min bar
    rows = {}
    _last_a = -1
    for t in read_jsonl(trades_path):
        _a = int(t.get("a", -1))
        if _a <= _last_a: continue
        _last_a = _a
        ts = int(t["T"]); b = pd.Timestamp(ts, unit="ms", tz="UTC").floor("5min")
        r = rows.setdefault(b, {"buy":0.0,"sell":0.0,"delta":0.0,"trades":0,"trade_qty":0.0})
        if bool(t.get("m", False)): r["sell"] += float(t["q"])
        else: r["buy"] += float(t["q"])
        r["delta"] += -float(t["q"]) if bool(t.get("m", False)) else float(t["q"])
        r["trades"] += 1; r["trade_qty"] += float(t["q"])

    # Marks
    for m in read_jsonl(mark_path):
        ts = int(m["E"]); b = pd.Timestamp(ts, unit="ms", tz="UTC").floor("5min")
        r = rows.setdefault(b, {"buy":0.0,"sell":0.0,"delta":0.0,"trades":0,"trade_qty":0.0})
        r.setdefault("mark", []).append(float(m["p"]))
        if m.get("r") is not None: r.setdefault("funding", []).append(float(m["r"]))

    # OI
    for x in read_jsonl(oi_path):
        ts = int(x.get("time", x.get("collector_recv_ms", 0))); b = pd.Timestamp(ts, unit="ms", tz="UTC").floor("5min")
        rows.setdefault(b, {"buy":0.0,"sell":0.0,"delta":0.0,"trades":0,"trade_qty":0.0}).setdefault("oi", []).append(float(x["openInterest"]))

    # Funding
    for x in read_jsonl(fund_path):
        ts = int(x.get("fundingTime", x.get("collector_recv_ms", 0))); b = pd.Timestamp(ts, unit="ms", tz="UTC").floor("5min")
        rows.setdefault(b, {"buy":0.0,"sell":0.0,"delta":0.0,"trades":0,"trade_qty":0.0}).setdefault("funding", []).append(float(x["fundingRate"]))

    # Checkpoints (rest-mode: each snapshot IS the book state)
    # NOTE: streaming (no sorted()) — checkpoints are appended chronologically
    # by the collector; materializing the full day (70MB+ JSON) OOMs the 2GB VPS.
    # Field name is always "E" (exchange event time in ms).
    for cp in read_jsonl(ckpt_path):
        try:
            ts = int(cp.get("E"))
        except (TypeError, ValueError, KeyError):
            continue
        if not ts: continue
        b = pd.Timestamp(ts, unit="ms", tz="UTC").floor("5min")
        r = rows.setdefault(b, {"buy":0.0,"sell":0.0,"delta":0.0,"trades":0,"trade_qty":0.0})
        bids = {float(pp): float(qq) for pp, qq in cp.get("bids", []) if float(qq) > 0}
        asks = {float(pp): float(qq) for pp, qq in cp.get("asks", []) if float(qq) > 0}
        bm = book_metrics(bids, asks, levels)
        r.setdefault("spread", []); r.setdefault("imb", []); r.setdefault("micro", [])
        r.setdefault("bd", []); r.setdefault("ad", []); r.setdefault("buy_impact", []); r.setdefault("sell_impact", [])
        r.setdefault("bid1", []); r.setdefault("ask1", [])
        if bm:
            r["depth_events"] = r.get("depth_events", 0) + 1
            for k, dst in [("spread_bps","spread"),("imbalance","imb"),("micro_edge_bps","micro"),
                           ("bid_depth","bd"),("ask_depth","ad"),("buy_impact_bps","buy_impact"),
                           ("sell_impact_bps","sell_impact"),("bid1_qty","bid1"),("ask1_qty","ask1")]:
                if np.isfinite(bm[k]): r[dst].append(bm[k])

    # Build dataframe
    out = []
    for b in sorted(rows):
        r = rows[b]
        total = r["buy"] + r["sell"]
        n_cp = r.get("depth_events", 0)
        # book_valid_fraction = % of 5m bar covered by at least one depth snapshot
        book_valid = 1.0 if (n_cp > 0 and total > 0) else 0.0
        row = {
            "date": b, "real_buy_volume": r["buy"], "real_sell_volume": r["sell"],
            "real_delta": r["delta"], "trade_count": r["trades"], "trade_volume": r["trade_qty"],
            "aggressive_buy_ratio": r["buy"]/total if total else np.nan,
            "l2_spread_bps": np.mean(r["spread"]) if r.get("spread") else np.nan,
            "l2_imbalance": np.mean(r["imb"]) if r.get("imb") else np.nan,
            "l2_microprice_edge_bps": np.mean(r["micro"]) if r.get("micro") else np.nan,
            "bid_depth": np.mean(r["bd"]) if r.get("bd") else np.nan,
            "ask_depth": np.mean(r["ad"]) if r.get("ad") else np.nan,
            "slippage_buy_10k_bps": np.mean(r["buy_impact"]) if r.get("buy_impact") else np.nan,
            "slippage_sell_10k_bps": np.mean(r["sell_impact"]) if r.get("sell_impact") else np.nan,
            "top_bid_qty": np.mean(r["bid1"]) if r.get("bid1") else np.nan,
            "top_ask_qty": np.mean(r["ask1"]) if r.get("ask1") else np.nan,
            "mark_price": np.mean(r["mark"]) if r.get("mark") else np.nan,
            "funding_rate": r["funding"][-1] if r.get("funding") else np.nan,
            "open_interest": r["oi"][-1] if r.get("oi") else np.nan,
            # L2 completeness bookkeeping
            "book_valid_fraction": book_valid,
            "depth_event_count": n_cp,
        }
        out.append(row)

    if not out: return None
    df = pd.DataFrame(out).sort_values("date").reset_index(drop=True)
    df["real_cvd"] = df["real_delta"].cumsum()
    df["delta_z"] = rolling_z(df["real_delta"].replace([np.inf,-np.inf], np.nan), 96, 24)
    df["cvd_slope"] = df["real_cvd"].diff(3)/3.0
    df["open_interest_change_pct"] = df["open_interest"].pct_change()*100.0
    df["feature_valid"] = (df["trade_count"] > 0)
    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--levels", type=int, default=5)
    ap.add_argument("--raw-root", default="user_data/data/orderflow_raw")
    ap.add_argument("--out-dir", default="/home/ubuntu/of-collector/data/features")
    args = ap.parse_args()

    root = Path(args.raw_root)
    symbol = args.symbol.upper()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Find all day files for this symbol
    d = root / symbol
    day_files = sorted([f.name for f in d.glob("*.trades.jsonl")])
    days = [f.replace(".trades.jsonl","") for f in day_files if f.startswith("2026-")]
    print(f"[{symbol}] {len(days)} days to process", flush=True)

    frames = []
    for day in days:
        print(f"[{symbol}] processing {day}...", flush=True)
        df = build_day(root, symbol, day, args.levels)
        if df is not None and len(df) > 0:
            frames.append(df)
            print(f"[{symbol}] {day}: {len(df)} rows", flush=True)

    if not frames:
        print(f"[{symbol}] NO DATA", flush=True)
        return
    final = pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    out_path = out_dir / f"{symbol}_5m.parquet"
    final.to_parquet(out_path, index=False)
    print(f"[{symbol}] wrote {len(final)} rows -> {out_path}")

if __name__ == "__main__":
    main()
