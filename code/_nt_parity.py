"""NautilusTrader cross-check of cbpack survivors.

Drives Nautilus with the pack's precomputed signals. Cost model: 7 bps/side
(5 fee + 2 slip approximated as taker fee). Entry/exit decisions follow the
pack's signal schedule; fills occur at Nautilus's bar-close market price, which
differs from the pack's next-open convention (documented below).
"""
import os, sys, math, json
import pandas as pd
from decimal import Decimal

ROOT = r"C:\Users\Lenovo\Documents\backtest-system"
sys.path.insert(0, os.path.join(ROOT, "code"))

# load pack engine
import types
_cbmod = types.ModuleType("cbpack_engine")
_cbmod.__file__ = os.path.join(ROOT, "code", "cbpack_engine.py")
sys.modules["cbpack_engine"] = _cbmod
exec(open(os.path.join(ROOT, "code", "cbpack_engine.py")).read(), _cbmod.__dict__)
prepare = _cbmod.prepare
attach_funding = _cbmod.attach_funding
BacktestConfig = _cbmod.BacktestConfig
backtest = _cbmod.backtest
make_signals = _cbmod.make_signals

from nautilus_trader.backtest import BacktestEngine
from nautilus_trader.backtest import BacktestEngineConfig
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.execution import MakerTakerFeeModel
from nautilus_trader.execution import ProbabilisticFillModel
from nautilus_trader.model import AccountType, Money, OmsType, Quantity, TraderId, Venue
from nautilus_trader.model import Currency
from nautilus_trader.model import Bar, BarType, BarSpecification
from nautilus_trader.model import BarAggregation, PriceType
from nautilus_trader.model import InstrumentId, Symbol
from nautilus_trader.model import CurrencyPair
from nautilus_trader.model import Price, OrderSide, TimeInForce
from nautilus_trader.trading import Strategy
from nautilus_trader.core.datetime import dt_to_unix_nanos

VENUE = Venue("SIM")
USD = Currency.from_str("USD")
XRP = Currency.from_str("XRP")
SOL = Currency.from_str("SOL")
BTC = Currency.from_str("BTC")
USD = USD

def load_df(sym):
    p = os.path.join(ROOT, "data", "binance_klines_1h_taker", f"{sym}_1h.csv")
    raw = pd.read_csv(p)
    raw.columns = [c.strip().lower() for c in raw.columns]
    raw = raw.rename(columns={"open_ts": "open_time"})
    raw["open_time"] = pd.to_datetime(raw["open_time"], unit="ms", utc=True)
    df = prepare(raw.set_index("open_time"))
    fp = os.path.join(ROOT, "data", "binance_funding", f"{sym}_funding.json")
    if os.path.exists(fp):
        recs = json.load(open(fp))
        idx = pd.DatetimeIndex(pd.to_datetime([x["t"] for x in recs], unit="ms", utc=True))
        _unit = getattr(df.index + pd.Timedelta(seconds=60), "unit", None)
        if _unit is not None and hasattr(idx, "as_unit"):
            idx = idx.as_unit(_unit)
        s = pd.Series([float(x["r"]) for x in recs], index=idx)
        s = s[~s.index.duplicated(keep="last")].sort_index()
        df = attach_funding(df, s)
    return df

def make_instrument(sym, prec_price, prec_size):
    # pick base currency
    
    base = XRP if sym.startswith("XRP") else (SOL if sym.startswith("SOL") else BTC)
    return CurrencyPair(
        instrument_id=InstrumentId(Symbol(f"{sym}"), VENUE),
        raw_symbol=Symbol(f"{sym}"),
        base_currency=base,
        quote_currency=USD,
        price_precision=prec_price,
        size_precision=prec_size,
        price_increment=Price.from_str("0.0001" if prec_price == 4 else "0.01"),
        size_increment=Quantity.from_str("0.01" if prec_size == 2 else ("0.1" if prec_size == 1 else "0.001")),
        lot_size=Quantity.from_str("0.01" if prec_size == 2 else ("0.1" if prec_size == 1 else "0.001")),
        max_quantity=Quantity.from_str("1000000"),
        min_quantity=Quantity.from_str("0.01" if prec_size == 2 else "0.1"),
        max_price=Price.from_str("100000"),
        min_price=Price.from_str("0.0001" if prec_price == 4 else "0.01"),
        margin_init=0.0,
        margin_maint=0.0,
        ts_event=0,
        ts_init=0,
    )

def run_one(sym, sid):
    print(f"\n===== {sym} {sid} =====")
    df = load_df(sym)
    sig = make_signals(df, sid)
    # pack reference
    r = backtest(df, sig, BacktestConfig())
    pm, pt, pe, ps = r.metrics, r.trades, r.equity, r.signals
    print(f"pack: net={pm['net_return_pct']:+.2f}% pf={pm['profit_factor']:.3f} trades={pm['n_trades']}")

    prec_price = 4 if sym.startswith("XRP") else 2
    prec_size = 2 if sym.startswith("XRP") else (1 if sym.startswith("SOL") else 3)
    instrument = make_instrument(sym, prec_price, prec_size)
    bar_type = BarType(instrument.id, BarSpecification(1, BarAggregation.HOUR, PriceType.LAST))

    # precompute signal arrays aligned to df
    buy = sig["buy"].to_numpy(bool)
    sell = sig["sell"].to_numpy(bool)
    exl = sig["exit_long"].to_numpy(bool)
    exs = sig["exit_short"].to_numpy(bool)
    print("DEBUG signals: buy=%d sell=%d exl=%d exs=%d" % (int(buy.sum()), int(sell.sum()), int(exl.sum()), int(exs.sum())))
    sl_d = sig["sl_dist"].to_numpy(float)
    tp_d = sig["tp_dist"].to_numpy(float)
    mh = int(sig["max_hold"].iloc[0])

    bars = []
    for i, (_, row) in enumerate(df.iterrows()):
        ts = dt_to_unix_nanos(row.name.to_pydatetime())
        bars.append(Bar(
            bar_type=bar_type,
            open=Price.from_str(f"{row['open']:.{prec_price}f}"),
            high=Price.from_str(f"{row['high']:.{prec_price}f}"),
            low=Price.from_str(f"{row['low']:.{prec_price}f}"),
            close=Price.from_str(f"{row['close']:.{prec_price}f}"),
            volume=Quantity.from_str(f"{row['volume']:.{prec_size}f}"),
            ts_event=ts,
            ts_init=ts,
        ))

    fills_log = []  # list of (side, price, qty, ts)
    equity_log = []

    class Strat(Strategy):
        def __init__(self):
            super().__init__()
            self.i = 0
            self.entry_price = None
            self.entry_ts = None
            self.pos_dir = 0
            self.pos_qty = 0.0
            self.entry_bar = None

        def on_start(self):
            print("ON_START: len(buy)=", len(buy), "sum=", int(buy.sum()), "len(sl_d)=", len(sl_d))
            self.subscribe_bars(bar_type)

        def on_bar(self, bar):
            idx = self.i
            self.i += 1
            if idx < 3:
                print("BAR idx=", idx, "buy[idx]=", bool(buy[idx]), "sl_d[idx]=", sl_d[idx])
            if idx >= len(df):
                return
            # risk sizing
            acct = self.cache.account_for_venue(VENUE)
            bal = float(acct.balance(USD).total) if acct else 10000.0
            price = float(bar.close)
            sl_dist = float(sl_d[idx])
            # entry decision
            want = 0
            if buy[idx]:
                want = 1
            elif sell[idx]:
                want = -1
            # exit decision for open position
            close_now = False
            why = None
            if self.pos_dir != 0:
                if (self.pos_dir == 1 and bool(exl[idx])) or (self.pos_dir == -1 and bool(exs[idx])):
                    close_now = True
                    why = "exit_signal"
                elif mh > 0 and (idx - self.entry_bar) + 1 >= mh:
                    close_now = True
                    why = "time_stop"
            # SL/TP intrabar check
            if self.pos_dir != 0 and not close_now:
                sl_level = self.entry_price - self.pos_dir * sl_dist
                tp_level = self.entry_price + self.pos_dir * (tp_d[idx] if (tp_d[idx] == tp_d[idx]) else float("nan"))
                has_tp = tp_d[idx] == tp_d[idx]
                hi = float(bar.high); lo = float(bar.low)
                if self.pos_dir == 1:
                    sl_hit = lo <= sl_level
                    tp_hit = has_tp and hi >= (self.entry_price + self.pos_dir * tp_d[idx])
                else:
                    sl_hit = hi >= sl_level
                    tp_hit = has_tp and lo <= (self.entry_price + self.pos_dir * tp_d[idx])
                if sl_hit or tp_hit:
                    close_now = True
                    why = "sl" if (sl_hit and (not tp_hit or sl_hit)) else "tp"

            # execute close
            if close_now and self.pos_dir != 0:
                o = self.order_factory.market(
                    instrument_id=instrument.id,
                    order_side=OrderSide.SELL if self.pos_dir == 1 else OrderSide.BUY,
                    quantity=Quantity.from_str(f"{abs(self.pos_qty):.{prec_size}f}"),
                    time_in_force=TimeInForce.GTC,
                )
                self.submit_order(o)
                fills_log.append(("close", price, abs(self.pos_qty), why, idx))
                self.pos_dir = 0
                self.pos_qty = 0.0
                self.entry_price = None

            if want != 0 and not hasattr(self, "_dbg"):
                self._dbg = True
                print("DBG first want!=0: idx=", idx, "want=", want, "sl_dist=", sl_dist, "pos_dir=", self.pos_dir, "sl_dist>0=", sl_dist > 0, "finite=", sl_dist == sl_dist)
            if idx == 0:
                print("DBG on_bar idx0: buy[0]=", bool(buy[0]), "len(buy)=", len(buy), "self.i=", self.i)
            if want != 0:
                print("DBG want!=0 idx=", idx, "sl_dist=", sl_dist, "pos_dir=", self.pos_dir)
            # execute open (if flat and want != 0)
            if self.pos_dir == 0 and want != 0 and sl_dist > 0 and (sl_dist == sl_dist):
                q = bal * 0.01 / sl_dist
                cap = bal * 3.0 / price
                q = min(q, cap)
                if q > 0:
                    qstr = f"{q:.{prec_size}f}"
                    try:
                        o = self.order_factory.market(
                            instrument_id=instrument.id,
                            order_side=OrderSide.BUY if want == 1 else OrderSide.SELL,
                            quantity=Quantity.from_str(qstr),
                            time_in_force=TimeInForce.GTC,
                        )
                        self.submit_order(o)
                        print("SUBMITTED", want, qstr, "sl_dist", sl_dist)
                    except Exception as e:
                        print("SUBMIT ERR:", repr(e))
                    self.pos_dir = want
                    self.pos_qty = q if want == 1 else -q
                    self.entry_price = price
                    self.entry_bar = idx
                    fills_log.append(("open", price, abs(q), "entry", idx))

        def on_order_filled(self, event):
            pass

    engine = BacktestEngine(config=BacktestEngineConfig(trader_id=TraderId("TRADER-001")))
    engine.add_venue(
        venue=VENUE,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=USD,
        starting_balances=[Money(10000, USD)],
        bar_execution=True,
        trade_execution=True,
        fee_model=MakerTakerFeeModel(maker_rate=Decimal("0.0007"), taker_rate=Decimal("0.0007")),
        fill_model=ProbabilisticFillModel(prob_fill_on_limit=1.0, prob_slippage=0.0, random_seed=42),
    )
    engine.add_instrument(instrument)
    engine.add_data(bars)
    strat = Strat()
    engine.add_strategy(strat)
    engine.run()

    # results
    acct = engine.cache.account_for_venue(VENUE)
    final_bal = float(acct.balance(USD).total)
    net_ret = (final_bal / 10000.0 - 1.0) * 100.0
    fills_report = engine.generate_order_fills_report()
    n_fills = len(fills_report) if fills_report is not None else 0
    # count round trips: opens
    n_opens = sum(1 for f in fills_log if f[0] == "open")
    print(f"nautilus: final_balance={final_bal:.2f} net={net_ret:+.2f}% fills={n_fills} opens={n_opens}")
    print(f"pack:     net={pm['net_return_pct']:+.2f}% pf={pm['profit_factor']:.3f} trades={pm['n_trades']}")
    # print fills report head
    if fills_report is not None and len(fills_report) > 0:
        print("fills_report columns:", list(fills_report.columns))
        print(fills_report.head(3).to_string())
    engine.dispose()
    return net_ret, n_opens

if __name__ == "__main__":
    for sym, sid in [("BTCUSDT", "S02"), ("BTCUSDT", "S10")]:
        run_one(sym, sid)
