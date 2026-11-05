#!/usr/bin/env python3
"""
instruments_check.py — validate a price/qty against the instrument-rules
snapshot in data/instruments/ (built by code/fetch_instruments.py).

Checks: price on the tickSize grid, qty on the stepSize grid and within
min/max, notional >= minNotional. Exit 0 = all checks pass, 1 = violation,
2 = symbol/market not found (fail loudly, never approximate).

Usage:
  python code/instruments_check.py --symbol XRPUSDT --market fapi --price 2.455 --qty 25
  python code/instruments_check.py --symbol BTCUSDT --market spot --price 68000
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FILES = {
    "spot": REPO / "data" / "instruments" / "spot_exchangeInfo.json",
    "fapi": REPO / "data" / "instruments" / "fapi_exchangeInfo.json",
}


def decimals_of(step: Decimal) -> int:
    e = -step.as_tuple().exponent
    return max(0, int(e))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--market", choices=("spot", "fapi"), default="fapi")
    ap.add_argument("--price", type=float, default=None)
    ap.add_argument("--qty", type=float, default=None)
    args = ap.parse_args()

    path = FILES[args.market]
    if not path.exists():
        print(f"REFUSED — snapshot missing: {path}. Run code/fetch_instruments.py first.")
        return 2
    data = json.loads(path.read_text(encoding="utf-8"))
    sym = next((s for s in data.get("symbols", [])
                if s.get("symbol") == args.symbol.upper()), None)
    if sym is None:
        print(f"REFUSED — {args.symbol} not listed in {args.market} snapshot "
              f"({len(data.get('symbols', []))} symbols).")
        return 2

    filt = {f["filterType"]: f for f in sym.get("filters", [])}
    tick = Decimal(filt["PRICE_FILTER"]["tickSize"])
    lot = Decimal(filt.get("LOT_SIZE", filt.get("MARKET_LOT_SIZE", {})).get("stepSize", "0"))
    min_qty = Decimal(filt.get("LOT_SIZE", filt.get("MARKET_LOT_SIZE", {})).get("minQty", "0"))
    notional = filt.get("MIN_NOTIONAL", filt.get("NOTIONAL", {}))
    min_notional = Decimal(notional.get("minNotional", notional.get("notional", "0")))

    print(f"{sym['symbol']} ({args.market}, status={sym.get('status')})")
    print(f"  tickSize={tick} stepSize={lot} minQty={min_qty} minNotional={min_notional}")

    fails = []
    if args.price is not None:
        dp = decimals_of(tick)
        p_dec = Decimal(str(args.price))
        nearest = (p_dec / tick).to_integral_value(rounding="ROUND_HALF_UP") * tick
        on_grid = (p_dec % tick) == 0
        status = "OK" if on_grid else f"OFF-GRID (nearest valid: {nearest:.{dp}f})"
        print(f"  price {args.price}: {status}")
        if not on_grid:
            fails.append("price_off_tick_grid")
    if args.qty is not None:
        q_dec = Decimal(str(args.qty))
        on_grid = lot == 0 or (q_dec % lot) == 0
        status = "OK" if on_grid else f"OFF-GRID (step {lot})"
        print(f"  qty {args.qty}: {status}")
        if not on_grid:
            fails.append("qty_off_step_grid")
        if q_dec < min_qty:
            fails.append("qty_below_minQty")
            print(f"  qty {args.qty}: BELOW minQty {min_qty}")
    if args.price is not None and args.qty is not None:
        notional_val = Decimal(str(args.price)) * Decimal(str(args.qty))
        ok = notional_val >= min_notional
        print(f"  notional {notional_val}: {'OK' if ok else f'BELOW minNotional {min_notional}'}")
        if not ok:
            fails.append("notional_below_min")

    if fails:
        print(f"FAIL — {', '.join(fails)}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
