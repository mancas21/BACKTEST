# === 6. Bollinger z-score reversion (solo en régimen lateral) ===
# Edge: reversion en régimen de baja tendencia (ADX < 20).
# INVERSA a tu estrategia original: aquí vender y comprar en los extremos.
def strat_bb_reversion(df, n=20, z_entry=2.0, adx_max=20, adx_period=14):
    ma = df.close.rolling(n).mean()
    sd = df.close.rolling(n).std()
    z = (df.close - ma) / sd
    # ADX simple
    up = df.high.diff().clip(lower=0)
    dn = (-df.low.diff()).clip(lower=0)
    tr = pd.concat([df.high - df.low, (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(adx_period).mean()
    di_p = 100 * up.rolling(adx_period).mean() / atr
    di_n = 100 * dn.rolling(adx_period).mean() / atr
    dx = 100 * (di_p - di_n).abs() / (di_p + di_n).replace(0, np.nan)
    adx = dx.rolling(adx_period).mean()
    lateral = adx < adx_max
    pos = pd.Series(0.0, index=df.index)
    pos[(z < -z_entry) & lateral] = 1.0
    pos[(z > z_entry) & lateral] = -1.0
    # Exit when z crosses 0
    for i in range(1, len(pos)):
        if pos.iloc[i - 1] != 0 and abs(z.iloc[i]) < 0.5:
            pos.iloc[i] = 0
    return pos

# === 7. RSI-2 Connors mean reversion (long only) ===
# Edge: oversold en tendencia alcista de largo plazo se recupera.
def strat_rsi2(df, rsi_len=2, entry=10, exit=60, trend_ema=200):
    delta = df.close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/rsi_len).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/rsi_len).mean()
    rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    trend = df.close > df.close.ewm(span=trend_ema).mean()
    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    for i in range(len(df)):
        if not in_pos and rsi.iloc[i] < entry and trend.iloc[i]:
            in_pos = True
        elif in_pos and rsi.iloc[i] > exit:
            in_pos = False
        pos.iloc[i] = 1.0 if in_pos else 0.0
    return pos

# === 8. Pairs trading BTC-ETH (cointegración rolling) ===
# Edge: el ratio BTC/ETH revierte. Log-spread z-score.
def strat_pairs(panel, symbol_a="BTC/USDT", symbol_b="ETH/USDT", lookback=168, z_entry=2.0):
    a = panel[symbol_a].close
    b = panel[symbol_b].close
    spread = np.log(a) - np.log(b)
    mu = spread.rolling(lookback).mean()
    sd = spread.rolling(lookback).std()
    z = (spread - mu) / sd
    pos_a = pd.Series(0.0, index=a.index)
    pos_a[z > z_entry] = -1.0   # short A when spread rich
    pos_a[z < -z_entry] = 1.0
    pos_a[z.abs() < 0.5] = 0.0  # exit
    pos_b = -pos_a * (b / a)  # beta neutral por ratio
    return {symbol_a: pos_a.ffill().fillna(0), symbol_b: pos_b.ffill().fillna(0)}

# === 9. VWAP deviation reversion (intraday) ===
# Edge: precios se alejan del VWAP intradía y revierten.
def strat_vwap_reversion(df, lookback=24, z_entry=2.0):
    pv = (df.close * df.volume).rolling(lookback).sum()
    v = df.volume.rolling(lookback).sum()
    vwap = pv / v
    dev = (df.close - vwap) / vwap
    z = (dev - dev.rolling(lookback).mean()) / dev.rolling(lookback).std()
    pos = pd.Series(0.0, index=df.index)
    pos[z > z_entry] = -1.0
    pos[z < -z_entry] = 1.0
    pos[z.abs() < 0.5] = 0.0
    return pos.ffill(limit=12).fillna(0)