# Pantalla tactil 2026-10-25 — cuatro familias, un solo veredicto

Coste: 22 pb roundtrip (modelo del repo). Datos: 1m taker 2024-10 -> 2026-10 (7 simbolos)
y 1h 2019/2020 -> 2026-10 (13 simbolos). Sin look-ahead: entrada al open siguiente.

## 1. Flujo 15m (Regla 7 a+b) — muerta
Proxy declarado: (a) CVD +2 barras; (b) >=3 sub-barras de 1m con >=65% compra.
No hay footprint por nivel en disco; el proxy es de barra, no de precio.

| simbolo | 3h bruto | base 3h | 6h bruto |
|---|---|---|---|
| BTC | +0.70 | +0.55 | +0.87 |
| ETH | +1.81 | +0.74 | +1.18 |
| SOL | -2.96 | +0.22 | -4.04 |
| SUI | +1.11 | +0.22 | +6.01 |
| XRP | -2.52 | +2.20 | +0.39 |
| HYPE | +1.91 | +4.37 | +6.90 |
| JUP | -3.07 | +0.89 | -0.38 |

Ningun horizonte (1h/2h/3h/6h) supera 22 pb. Anio por anio, neto negativo en los 7
simbolos y los 3 anios. Filtro EMA200: peor. Regla 2 (spike delta): +1.0 pb bruto.

## 2. Pullback en tendencia 1h — muere en walk-forward
Regimen close>EMA200, toque EMA20 o RSI<40, gatillo cierre>max(high) previo,
stop min(low,6)-0.25ATR, objetivo 2R, hold max 72.

- 10.843 trades / 13 simbolos. PF neto 0.962, -7.9 pb/trade, 36.1% win.
- Bruto +14.05 pb/trade: el edge existe pero es menor que el coste taker.
- Con maker-in 2pb / taker-out 5pb (7 pb): PF 1.036, +7.05 pb, 2/3 tercios verdes.
- **Walk-forward: train 2023-24 PF 1.121 (+24.6 pb) -> OOS 2025-26 PF 0.834 (-31.4 pb).**
- Falla el gate 5. No se puede enviar.

## 3. Breakout con expansion ATR 1h — muerta
5.923 trades, PF 0.863, -17.2 pb/trade, 34.9% win. Solo DOGE y SUI ~0.

## 4. Tendencia diaria (6-7 anios, 13 simbolos) — muere en OOS
| variante | PF train 2019-24 | PF OOS 2025-26 | OOS PF>1.2 |
|---|---|---|---|
| EMA50 long/flat | 1.32 | 1.01 | 0/11 |
| EMA200 long/flat | 1.30 | 0.93 | 0/11 |
| EMA50+EMA200 | 1.36 | 0.88 | 0/11 |
| EMA50 long/short | 1.13 | 1.02 | 0/11 |
| EMA200 long/short | 1.12 | 0.97 | 0/11 |
| histeresis long/short | 1.15 | 1.01 | 0/11 |

En muestra completa la tendencia diaria luce (PF 1.10-1.43, 12/13 positivos,
Calmar 0.79 vs 0.48 de buy&hold), pero **el unico tramo que importa (2025-26) la deja
en PF ~1.0 y Sharpe ~0**. El edge es de 2021-2024, no de ahora.

## Veredicto
Cuatro familias direccionales, 7 anios, 13 simbolos, 22 pb: **ninguna sobrevive OOS**.
La puerta NEUTRAL no esta rota: no hay direccion que emitir en este regimen.
Lo unico validado sigue siendo captura de rango con ejecucion maker (grid neutral XRP,
2 pb), que es precisamente la familia que NO necesita direccion.

## Siguiente paso acordado
No abrir la puerta. Llevar el esfuerzo a la familia que paga en 2025-26 (rango/maker)
y usar el flujo solo como contexto, nunca como sesgo.

Artefactos: tactical_screen_2026-10-25.json, tactical_h1_trades_7bp_2026-10-25.csv
