"""Diez estrategias/familias de senales para el mismo motor. Cada una es una funcion CAUSAL df -> columnas de features.
El modelo walk-forward calibra p(up en h barras) a partir de ellas; la decision, costos, riesgo y controles son identicos
para todas, asi que la comparacion es justa. Todas usan solo datos <= cierre de la barra t."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict

import numpy as np
import pandas as pd

from .config import BotConfig


def _lr(df): return np.log(df["close"]).diff()


def tsmom(df, sig, cfg):
    c = df["close"]
    return pd.DataFrame({f"mom{k}": np.log(c / c.shift(k)) / (sig * np.sqrt(k)) for k in (6, 24, 96)})


def ema_reversion(df, sig, cfg):
    lc, out = np.log(df["close"]), {}
    for span in (12, 48):
        out[f"dev{span}"] = (lc - np.log(df["close"].ewm(span=span, min_periods=span).mean())) / (sig * np.sqrt(span))
    return pd.DataFrame(out)


def donchian(df, sig, cfg, n: int = 48):
    c, hi, lo = df["close"], df["high"].rolling(n).max(), df["low"].rolling(n).min()
    up = (np.log(c / df["high"].rolling(n).max().shift(1))) / sig
    dn = (np.log(c / df["low"].rolling(n).min().shift(1))) / sig
    return pd.DataFrame({"rpos": (c - lo) / (hi - lo) - 0.5, "brk_up": up.clip(lower=0), "brk_dn": dn.clip(upper=0)})


def vol_squeeze(df, sig, cfg):
    lr = _lr(df)
    vs = lr.rolling(24).std()
    lv = np.log(vs / vs.rolling(288, min_periods=96).mean())
    r1, r3 = lr / sig, np.log(df["close"] / df["close"].shift(3)) / (sig * np.sqrt(3))
    return pd.DataFrame({"log_vsq": lv, "r1n": r1, "r1n_x_sq": r1 * -lv, "r3n_x_sq": r3 * -lv})


def taker_flow(df, sig, cfg):
    imb = 2.0 * df["taker_buy_base"] / df["volume"].replace(0, np.nan) - 1.0
    out = {}
    for span in (3, 12):
        e = imb.ewm(span=span, min_periods=2).mean()
        out[f"imb_z{span}"] = (e - e.rolling(288, min_periods=72).mean()) / e.rolling(288, min_periods=72).std()
    return pd.DataFrame(out)


def cvd_divergence(df, sig, cfg, n: int = 48):
    delta = 2.0 * df["taker_buy_base"] - df["volume"]
    cvd = delta.rolling(n).sum() / df["volume"].rolling(n).sum().replace(0, np.nan)
    cvd_z = (cvd - cvd.rolling(288, min_periods=96).mean()) / cvd.rolling(288, min_periods=96).std()
    pz = np.log(df["close"] / df["close"].shift(n)) / (sig * np.sqrt(n))
    return pd.DataFrame({"cvd_z": cvd_z, "pz48": pz, "div": cvd_z - pz})


def vwap_deviation(df, sig, cfg):
    n = max(12, int(480 / cfg.interval_min))                    # sesion ~ 8 h (ciclo de funding)
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    vwap = (tp * df["volume"]).rolling(n).sum() / df["volume"].rolling(n).sum().replace(0, np.nan)
    dev = np.log(df["close"] / vwap) / sig
    return pd.DataFrame({"vwap_dev": dev, "vwap_dev_chg": dev.diff(6)})


def volume_shock(df, sig, cfg):
    lv = np.log(df["volume"].replace(0, np.nan))
    vz = (lv - lv.rolling(288, min_periods=96).mean()) / lv.rolling(288, min_periods=96).std()
    lr = _lr(df)
    r1 = lr / sig
    r3 = np.log(df["close"] / df["close"].shift(3)) / (sig * np.sqrt(3))
    big = (vz > 1.5).astype(float)
    return pd.DataFrame({"vz": vz, "r1_x_shock": r1 * big, "r3_x_shock": r3 * big})


def autocorr_regime(df, sig, cfg):
    lr = _lr(df)
    ac = lr.rolling(96).corr(lr.shift(1))
    r1, r3 = lr / sig, np.log(df["close"] / df["close"].shift(3)) / (sig * np.sqrt(3))
    return pd.DataFrame({"ac": ac, "ac_x_r1": ac * r1, "ac_x_r3": ac * r3})


def calendar_funding(df, sig, cfg):
    t = df.index
    h = t.hour.values + t.minute.values / 60.0
    d = t.dayofweek.values
    return pd.DataFrame({"sin24": np.sin(2 * np.pi * h / 24), "cos24": np.cos(2 * np.pi * h / 24),
                         "sin8": np.sin(2 * np.pi * h / 8), "cos8": np.cos(2 * np.pi * h / 8),
                         "sinw": np.sin(2 * np.pi * d / 7), "cosw": np.cos(2 * np.pi * d / 7)}, index=t)


@dataclass
class Strategy:
    id: str
    name: str
    thesis: str
    fn: Callable


REGISTRY: Dict[str, Strategy] = {s.id: s for s in [
    Strategy("S01", "Vol-normalised time-series momentum", "Retornos recientes (6/24/96 barras) normalizados por sigma continuan en la misma direccion (tendencia).", tsmom),
    Strategy("S02", "EMA z-score mean reversion", "La desviacion del precio respecto a su EMA (12/48) revierte (sobreextension).", ema_reversion),
    Strategy("S03", "Donchian range position / breakout", "Posicion en el rango de 48 barras y rupturas del maximo/minimo previos anticipan continuacion o rechazo.", donchian),
    Strategy("S04", "Volatility squeeze -> expansion", "Tras compresion de volatilidad, el movimiento de la ultima barra senala la direccion de la expansion.", vol_squeeze),
    Strategy("S05", "Taker-flow imbalance (OFI proxy)", "El desequilibrio comprador/vendedor agresor (taker buy / volumen) predice la siguiente direccion.", taker_flow),
    Strategy("S06", "CVD / price divergence", "Divergencia entre delta acumulado normalizado y precio (absorcion) anticipa reversion o continuacion.", cvd_divergence),
    Strategy("S07", "Rolling-VWAP deviation", "El precio gravita hacia el VWAP de la sesion de funding (8 h); la desviacion predice reversion.", vwap_deviation),
    Strategy("S08", "Volume-shock follow-through", "Movimientos con volumen anormal (z > 1.5) tienen continuacion o rebote distinto al ruido normal.", volume_shock),
    Strategy("S09", "Autocorrelation regime switch", "La autocorrelacion rolling del retorno (96 barras) decide si la ultima barra continua (AC>0) o revierte (AC<0).", autocorr_regime),
    Strategy("S10", "Calendar / funding-clock seasonality", "Hora del dia (24 h), ciclo de funding (8 h) y dia de la semana tienen drift sistematico.", calendar_funding),
]}


def strategy_frame(sid: str, df: pd.DataFrame, cfg: BotConfig, base: pd.DataFrame):
    """base = build_features(df,cfg) (aporta sig, fwd_ret, y). Devuelve (frame, columnas de features)."""
    cols = REGISTRY[sid].fn(df, base["sig"], cfg).replace([np.inf, -np.inf], np.nan)
    return base[["sig", "fwd_ret", "y"]].join(cols), list(cols.columns)
