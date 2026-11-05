# === 1. Time Series Momentum (TSMOM) con vol targeting ===
# Edge: crypto tiene momentum persistente a 2-8 semanas (Moskowitz-Ooi-Pedersen).
# Bajo Sharpe individual pero estable y con poca correlación a otros.
def strat_tsmom(df, lookback=168, vol_target=0.20, bars_per_year=8760):
    logret = np.log(df.close).diff()
    mom = np.log(df.close).diff(lookback)
    vol = logret.rolling(lookback).std() * np.sqrt(bars_per_year)
    scale = (vol_target / vol).clip(0, 2)
    pos = np.sign(mom) * scale
    return pos.clip(-1, 1).fillna(0)

# === 2. Donchian breakout con filtro de volatilidad ===
# Edge: rupturas de máximos con expansión de ATR capturan regímenes de tendencia.
def strat_donchian(df, n=100, atr_period=14, atr_mult=1.5):
    hi = df.high.rolling(n).max()
    lo = df.low.rolling(n).min()
    atr = (df.high - df.low).rolling(atr_period).mean()
    long_ = df.close > hi.shift(1)
    short_ = df.close < lo.shift(1)
    pos = pd.Series(0.0, index=df.index)
    pos[long_] = 1.0
    pos[short_] = -1.0
    # only take if recent range > atr_mult * atr (vol expansion)
    expansion = (hi - lo) > atr_mult * atr
    return (pos * expansion.astype(float)).fillna(0)

# === 3. HTF alignment: precio > EMA200 diaria y EMA50 > EMA200 (long only) ===
# Edge: filtro macro-regimen. Reduce falsos positivos de trend following.
def strat_htf_trend(df, fast=50, slow=200, hold=24):
    ema_f = df.close.ewm(span=fast).mean()
    ema_s = df.close.ewm(span=slow).mean()
    cond = (df.close > ema_s) & (ema_f > ema_s)
    # forward-fill with limited hold (memoria de posición)
    pos = cond.astype(float).replace(0, np.nan).ffill(limit=hold).fillna(0)
    return pos * 2 - 1  # -1 cuando cond es False

# === 4. Cross-sectional momentum (top-K alts) ===
# Edge: momentum cross-seccional (Jegadeesh-Titman) funciona en crypto.
# Necesita universe -> el runner debe manejar múltiples símbolos.
def strat_xs_momentum(panel: dict, lookback=720, top_k=3, rebalance=24):
    """panel: dict[symbol -> df]. Devuelve dict[symbol -> position]."""
    closes = pd.DataFrame({s: d.close for s, d in panel.items()}).dropna()
    mom = np.log(closes).diff(lookback)
    ranks = mom.rank(axis=1, pct=True)
    weights = (ranks > 1 - top_k / len(closes.columns)).astype(float)
    weights = weights.div(weights.sum(axis=1).replace(0, 1), axis=0)
    positions = {}
    for s in closes.columns:
        w = weights[s]
        # Rebalseo: mantener solo cada `rebalance` barras (sample & hold)
        reb = w.iloc[::rebalance].reindex(w.index).ffill()
        positions[s] = reb.fillna(0)
    return positions

# === 5. Breakout de rango + volumen ===
# Edge: rupturas con volumen > 2σ capturan movimientos reales vs fakeouts.
def strat_breakout_volume(df, n=48, vol_mult=2.0):
    hi = df.high.rolling(n).max().shift(1)
    lo = df.low.rolling(n).min().shift(1)
    avg_vol = df.volume.rolling(n).mean()
    breakout_up = (df.close > hi) & (df.volume > vol_mult * avg_vol)
    breakout_dn = (df.close < lo) & (df.volume > vol_mult * avg_vol)
    pos = pd.Series(0.0, index=df.index)
    pos[breakout_up] = 1
    pos[breakout_dn] = -1
    return pos.ffill(limit=24).fillna(0)