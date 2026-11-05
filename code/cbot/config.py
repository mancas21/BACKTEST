"""BotConfig -- reconstructed from the call sites in the pack's own suite.py.

Every field here is one the present code actually reads:
    suite.py      symbol, interval_min, horizon_bars, fee_taker, slippage,
                  funding_8h, min_edge   (via dataclasses.replace for the gross run)
    strategies.py interval_min (S07's session length), vol_window (base sig)
    model.py      train_bars / refit_every / min_train  (walk-forward)
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class BotConfig:
    symbol: str = "BTCUSDT"
    interval_min: int = 5
    horizon_bars: int = 3            # suite.py default: "holding 3 bars"

    # costs, per side. suite.py prints these as taker 0.05% + slippage 0.01%/side
    fee_taker: float = 0.0005
    slippage: float = 0.0001
    funding_8h: float = 0.0001
    min_edge: float = 0.0

    # per-bar volatility used as `sig` by every strategy
    vol_window: int = 24

    # walk-forward
    train_bars: int = 17500          # ~60 days of 5m bars
    refit_every: int = 1000
    min_train: int = 5000

    # decision
    edge_z: float = 1.0              # scale on the expected-move estimate
