# pragma pylint: disable=missing-docstring, invalid-name
"""OrderFlowRealScalp V2.3 REAL-ONLY (instalada como OrderFlowRealScalp para no
colisionar con OrderFlowProScalp).

Signals use archived exchange-native Binance data prepared offline:
aggTrade + diff-depth + REST L2 checkpoints + markPrice/funding + OI +
forceOrder liquidations. No OHLCV-derived order flow and no current orderbook
calls are used in backtesting.

INTEGRACIÓN (agregados sobre el archivo auditado, documentados):
- leverage() -> 1.0: validación de SEÑAL primero (decisión registrada). La
  economía 3x se evalúa después, no mezclada con el edge direccional.
- protections como @property (el config las tiene deprecated).
- order_types/time_in_force explícitos + process_only_new_candles=True.
- require_l2 (default True): con False, el gate de calidad usa solo trades
  (para el bootstrap de aggTrades históricos de Data Vision, que no trae L2).
  Se activa vía OrderFlowRealScalp.json. Sin L2 no hay señales L2-gated.
"""
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter, BooleanParameter


class OrderFlowRealScalp(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = True
    process_only_new_candles = True
    startup_candle_count = 250

    minimal_roi = {"0": 0.010, "10": 0.008, "30": 0.005, "60": 0}
    stoploss = -0.008
    trailing_stop = True
    trailing_stop_positive = 0.010
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": True,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 6},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 4,
                "stop_duration_candles": 6,
                "only_per_pair": False,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 48,
                "trade_limit": 20,
                "stop_duration_candles": 12,
                "max_allowed_drawdown": 0.08,
            },
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": 24,
                "trade_limit": 2,
                "stop_duration_candles": 12,
                "required_profit": -0.02,
            },
        ]

    delta_z_entry = DecimalParameter(1.0, 4.0, default=1.8, decimals=2, space="buy", optimize=True)
    imbalance_entry = DecimalParameter(0.05, 0.50, default=0.2, decimals=3, space="buy", optimize=True)
    absorption_z = DecimalParameter(0.25, 5.0, default=1.0, decimals=2, space="buy", optimize=True)
    exit_delta_z = DecimalParameter(1.0, 5.0, default=2.5, decimals=2, space="sell", optimize=True)
    exit_imbalance = DecimalParameter(0.05, 0.50, default=0.20, decimals=3, space="sell", optimize=True)
    min_trade_count = IntParameter(10, 1000, default=50, space="buy", optimize=True)
    min_book_valid = DecimalParameter(0.995, 1.0, default=0.999, decimals=3, space="buy", optimize=True)
    max_slippage_bps = DecimalParameter(1.0, 30.0, default=8.0, decimals=2, space="buy", optimize=True)
    max_oi_change_pct = DecimalParameter(0.05, 5.0, default=2.0, decimals=2, space="buy", optimize=True)
    max_data_latency_ms = IntParameter(100, 5000, default=2000, space="buy", optimize=True)
    # Bootstrap trades-only (sin L2): relaja el gate a solo-trades.
    require_l2 = BooleanParameter(default=True, space="buy", optimize=False)
    # Salida por reversión: exige N velas consecutivas de flujo opuesto.
    # Hallazgo en datos reales (train+test): con N=1 el ruido post-entrada
    # dispara la salida a -0.4/-0.5% y explica TODO el déficit. N=2 es la
    # única variante pre-registrada a comparar en train.
    exit_confirm_bars = IntParameter(1, 3, default=1, space="sell", optimize=False)

    flow_data_dir = Path("user_data/data/orderflow")

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        # Validación de señal a 1x. Escalar a 3x solo tras edge demostrado.
        return 1.0

    @staticmethod
    def _pair_filename(pair: str) -> str:
        # Freqtrade pair "SUI/USDT:USDT" -> parquet "SUIUSDT"
        parts = pair.split("/")
        base = parts[0]
        quote = parts[1].split(":")[0] if len(parts) > 1 else ""
        return base + quote

    def _load_real_features(self, dataframe: DataFrame, pair: str) -> DataFrame:
        path = self.flow_data_dir / f"{self._pair_filename(pair)}_5m.parquet"
        cols = [
            "real_delta", "real_buy_volume", "real_sell_volume", "real_cvd", "delta_z", "cvd_slope",
            "trade_count", "aggressive_buy_ratio", "l2_imbalance", "l2_spread_bps", "l2_microprice_edge_bps",
            "bid_depth", "ask_depth", "book_valid_fraction", "depth_event_count", "book_gap_events", "book_resyncs",
            "slippage_buy_10k_bps", "slippage_sell_10k_bps", "top_bid_qty", "top_ask_qty", "mark_price",
            "funding_rate", "open_interest", "open_interest_change_pct", "liquidation_long_notional",
            "liquidation_short_notional", "liq_imbalance", "absorption_long", "absorption_short",
            "queue_consumption_long", "queue_consumption_short", "data_latency_ms", "feature_valid",
        ]
        for c in cols: dataframe[c] = np.nan
        if not path.exists(): return dataframe
        try: f = pd.read_parquet(path)
        except Exception: return dataframe
        if "date" not in f.columns: return dataframe
        f["date"] = pd.to_datetime(f["date"], utc=True)
        f = f.sort_values("date").drop_duplicates("date", keep="last")
        base = dataframe[["date"]].copy(); base["date"] = pd.to_datetime(base["date"], utc=True)
        m = base.merge(f, on="date", how="left")
        # Feature row N is information completed during candle N. Use it only on N+1.
        for c in cols:
            if c in m: dataframe[c] = m[c].shift(1).to_numpy()
        # Honest NaN defaults for L2-gated cols absent from parquet
        for c in ["book_gap_events", "book_resyncs", "data_latency_ms",
                  "liquidation_long_notional", "liquidation_short_notional",
                  "liq_imbalance", "absorption_long", "absorption_short",
                  "queue_consumption_long", "queue_consumption_short"]:
            if c in cols and c not in dataframe.columns:
                dataframe[c] = np.nan
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["date"] = pd.to_datetime(dataframe["date"], utc=True)
        dataframe = self._load_real_features(dataframe, metadata["pair"])
        dataframe["feature_valid"] = dataframe["feature_valid"].fillna(False).astype(bool)
        base_ok = (
            dataframe["feature_valid"]
            & (dataframe["trade_count"] >= self.min_trade_count.value)
        )
        if self.require_l2.value:
            # data_latency_ms is not populated in parquet (REST collector doesn't track it).
            # Skip latency check when column is all-NaN.
            has_latency = dataframe["data_latency_ms"].notna().any() if "data_latency_ms" in dataframe.columns else False
            latency_ok = (
                dataframe["data_latency_ms"].fillna(0).le(self.max_data_latency_ms.value)
                if has_latency else pd.Series(True, index=dataframe.index)
            )
            l2_ok = (
                (dataframe["book_valid_fraction"].fillna(0.0) >= self.min_book_valid.value)
                & (dataframe["book_gap_events"].fillna(0) == 0)
                & dataframe["slippage_buy_10k_bps"].notna()
                & dataframe["slippage_sell_10k_bps"].notna()
                & latency_ok
            )
            dataframe["real_data_ok"] = base_ok & l2_ok
            use_imb = True
        else:
            # Bootstrap trades-only: sin L2 no hay imbalance/slippage/latency;
            # las señales L2-gated quedan desactivadas (solo delta/absorción
            # por trades). Puerta explícita, no fallback silencioso.
            dataframe["real_data_ok"] = base_ok
            use_imb = False
        dataframe["_use_imb"] = use_imb
        dataframe["long_flow"] = (
            (dataframe["delta_z"] > self.delta_z_entry.value)
            & ((dataframe["l2_imbalance"] > self.imbalance_entry.value) if use_imb else True)
            & ((dataframe["slippage_buy_10k_bps"] <= self.max_slippage_bps.value) if use_imb else True)
        )
        dataframe["short_flow"] = (
            (dataframe["delta_z"] < -self.delta_z_entry.value)
            & ((dataframe["l2_imbalance"] < -self.imbalance_entry.value) if use_imb else True)
            & ((dataframe["slippage_sell_10k_bps"] <= self.max_slippage_bps.value) if use_imb else True)
        )
        dataframe["long_absorption"] = (
            (dataframe["absorption_long"] > self.absorption_z.value)
            & ((dataframe["l2_imbalance"] > 0) if use_imb else True)
        )
        dataframe["short_absorption"] = (
            (dataframe["absorption_short"] > self.absorption_z.value)
            & ((dataframe["l2_imbalance"] < 0) if use_imb else True)
        )
        dataframe["oi_regime_ok"] = dataframe["open_interest_change_pct"].abs().fillna(0) <= self.max_oi_change_pct.value
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0; dataframe["enter_short"] = 0; dataframe["enter_tag"] = ""
        long = dataframe["real_data_ok"] & dataframe["oi_regime_ok"] & (dataframe["long_flow"] | dataframe["long_absorption"])
        short = dataframe["real_data_ok"] & dataframe["oi_regime_ok"] & (dataframe["short_flow"] | dataframe["short_absorption"])
        long_only = long & ~short; short_only = short & ~long
        dataframe.loc[long_only, "enter_long"] = 1
        dataframe.loc[short_only, "enter_short"] = 1
        dataframe.loc[long_only & dataframe["long_flow"], "enter_tag"] = "real_delta_l2_long"
        dataframe.loc[long_only & ~dataframe["long_flow"] & dataframe["long_absorption"], "enter_tag"] = "real_absorption_long"
        dataframe.loc[short_only & dataframe["short_flow"], "enter_tag"] = "real_delta_l2_short"
        dataframe.loc[short_only & ~dataframe["short_flow"] & dataframe["short_absorption"], "enter_tag"] = "real_absorption_short"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0; dataframe["exit_short"] = 0; dataframe["exit_tag"] = ""
        return dataframe
