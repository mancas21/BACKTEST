# SMQE v1.1 (adjunto del usuario) — veredicto

## VEREDICTO: KILLED como candidato — ninguna celda pasa todos los gates

Cinco símbolos a una hora, dos regímenes de costes (repo con funding real
cobrado en los asentamientos reales; pine tal como se distribuye). Cuatro de
cinco símbolos pierden antes o con costes del repo (factor de beneficio por
debajo de uno en BTC, ETH, SOL y XRP). La celda más cercana, SUI a una hora
con costes del repo y funding real, supera los seis gates de criba pero FALLA
el gate de significancia: el intervalo de confianza bootstrap del P&L medio
por trade incluye el cero. Con la barra de la casa (el IC por encima de cero
que exigimos a todo candidato), no hay superviviente.

La familia ya tenía antecedentes: el núcleo CVRMD (señal del v1.1) estaba
marcado como frágil y sensible a la muestra en SUI y ETH, y el porte anterior
del SMQE v2 quedó suspendido por imposibilidad de OOS en SUI. Este resultado
lo reconfirma con artefactos: el borde sobrevive solo en el símbolo más joven
del universo, con cincuenta y tres trades, y no alcanza significancia.

## Qué se portó

Fuente de registro: `code/smqe_v1_1_strategy.pine` (adjunto copiado
byte-idéntico). El núcleo de señal es el CVRMD validado (divergencia del
histograma MACD en pivotes estrictos de tres por lado, banda VWAP de sesión
más menos una desviación típica, pendiente del proxy CVD, filtro RSI) con
todas las gates de confluencia en su valor de fábrica, apagadas — el propio
Pine las declara fuera del backtest validado. El simulador de ejecución v1.1
está portado verbatim: fill al cierre de la barra de señal, stop de ATR
congelado, objetivo uno a mitad de posición (VWAP solo si es favorable y
queda estrictamente dentro del objetivo dos; si no, R fijo), objetivo dos al
resto, flip en señal opuesta con reentrada en la misma barra, cooldown sobre
entradas y flips, stop primero en empates intrabar, comisión en cada fill
dentro del P&L del trade, y drawdown mark-to-market.

Las primitivas de señal se importan POR IDENTIDAD del motor del v2 (auditado
antes de ningún dato real). El porte nuevo pasó su propia auditoría
`code/_smqe11_audit.py` antes de ningún artefacto con datos reales: veintinueve
comprobaciones, todas en verde — respuestas conocidas de cada regla de
ejecución (objetivos, stop en los tres modos de fill, flip con reversa,
cooldown, funding, comisión de entrada dentro del P&L, drawdown, cierre forzoso
por fin de datos), identidad de primitivas, paridad de coste cero,
determinismo y prueba de no anticipación por truncado. Cuatro fallos de la
primera pasada fueron del TEST, no del motor (aritmética del modo emulador,
precio de fill del stop, un caso cuyo cooldown no era observable, y comparación
de NaN) — la lección auditada, otra vez.

Adapter `smqe11` en `ADAPTERS`; solo una hora (el factor de funding del motor
lo asume).

## Las diez celdas (run_id citado por línea)

Costes del repo (cinco por mil de fee más medio punto por lado, funding real
cobrado en asentamientos reales del fichero de funding):

- BTCUSDT `9e38c42795c60025` — PF 0.556, net -26.11%, n 98, OOS PF 0.531 → KILL (pierde con costes; funding pagado 1272.84).
- ETHUSDT `5fc1257c74580c66` — PF 0.896, net -5.14%, n 94, concentración rota (sin sus cinco mejores trades: -14.94%) → KILL.
- SOLUSDT `5f99330b4d4c7515` — PF 0.748, net -14.63%, n 84 → KILL. La misma señal a costes pine `2bdc4afdf0d51f93` gana +14.99% (PF 1.424): un giro de costes de casi treinta puntos sobre ochenta y cuatro trades — la clase "los costes lo destruyen".
- XRPUSDT `5621e1453978d5f6` — PF 0.922, net -4.44%, n 102 → KILL.
- SUIUSDT `da87389998c1153c` — PF 1.543, net +11.81%, n 53, win 45.3%, 3/3 tercios verdes, OOS PF 1.303 con +2.53%, best-5 el 80.1% del PnL (sin ellos +2.34%), excess +47.4pp contra un buy&hold de -35.6% → pasa los gates de criba y FALLA la significancia: IC bootstrap [-8.32, +53.55], P(media menor o igual a cero) 0.0835.

Tal como se distribuye (comisión de seis por mil por lado, funding apagado —
el modo por defecto del Pine, declarado):

| símbolo | run_id | PF | net % | IC bootstrap |
|---|---|---|---|---|
| BTCUSDT | `c4849cd3e89641e2` | 0.687 | -16.59 | [-35.38, +2.27] |
| ETHUSDT | `b21cd3f646b96d1b` | 0.952 | -2.11 | [-21.99, +17.65] |
| SOLUSDT | `2bdc4afdf0d51f93` | 1.424 | +14.99 | [-6.15, +42.09] |
| XRPUSDT | `97ae6b95c151a649` | 1.019 | +0.90 | [-18.65, +20.91] |
| SUIUSDT | `628003fe77ab72f8` | 1.675 | +14.65 | [-3.42, +59.79] |

## SUI: estabilidad de vecindario y scorecard

Vecindario en SUIUSDT con costes del repo y funding real, STABLE en ambos
parámetros declarados: `atr_mult` en 1.0/1.5/2.0 → PF 1.44/1.54/1.57
(`ffdefa4a491cb632`, `16413c6afc01ef7e`, `9be8b04747f694c0`); `tp2_r` en
1.5/2.0/2.5 → PF 1.51/1.54/1.66 (`a4a9b6964851e140`, `b02f8dc02a5ed690`,
`4f94171ebf5f3ae7`). El gate de cooldown resultó inerte en esta muestra (sus
valores vecinos no cambian ningún número; se declara, no se cita).

Scorecard (`vrun stats` sobre `da87389998c1153c`): Ljung-Box acepta
independencia; Calmar bajo; el bootstrap por bloques del scorecard coincide en
la conclusión con el del artefacto — el intervalo incluye el cero.

## Reservas declaradas

- Funding: cobrado en los asentamientos reales del fichero; el fichero de
  funding termina antes que las klines (la brecha conocida del manifiesto),
  así que los últimos días de la ventana no llevan funding. Ver
  `datacheck_funding.py` antes de citar la cola.
- La celda superviviente es la survivor de diez evaluadas: el haircut de
  multiplicidad se aplica entero.
- OOS por split congelado setenta-treinta, contaminación de selección nula
  dentro de la celda pero la ELECCIÓN de la celda es post-hoc.
- G11 (tasa de acierto mínima contra el breakeven) no aplica a esta tasa de
  acierto.

## Próximo paso según doctrina

Ninguna re-corrida puede revivir esto. Si la idea sigue viva para el usuario,
el único camino que acepta el repo es un registro forward en papel sobre
barras nuevas para la celda de SUI — igual que se hizo con la lista TOP10 —
y la puerta de la casa es el IC bootstrap: con cincuenta y tres trades y este
P&L por trade, la significancia no llega.
