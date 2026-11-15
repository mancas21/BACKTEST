# htf_ltf_fvg (4H FVG -> 15M tap -> 15M FVG entry) — veredicto de campaña

## VEREDICTO: KILLED — cero de doce celdas pasa la batería estándar; el modo limit (el mejor) además no es certificable por fill-model

El pack adjunto (Python, copiado byte-idéntico como
`code/htf_ltf_fvg_strategy.py`, sha256 4b96cf6e...) implementa la estrategia
"4H FVG -> 15M tap -> nueva 15M FVG" con dos motores independientes
(vector y evento) que deben coincidir trade a trade, convenciones
no-lookahead declaradas (una FVG de 4H solo se conoce al cierre de 4H;
SL primero en barras que abarcan ambos; fills de hueco en la apertura;
maker en entrada limit y TP, taker en el resto). Porte como adapter
`htffvg` (`code/htffvg_engine.py`) que alimenta los klines de 15m del repo
hasheados, exige la paridad dentro del artefacto y añade la batería
estándar. Auditoría `code/_htffvg_audit.py`: cuarenta y cinco respuestas
conocidas ALL PASS antes de datos reales (toda la primera corona fue del
test: escenarios sin zona 4H real, un 15M-FVG que no era FVG, y dos
convenciones del pack que el test había mal leído — el sl_ref de la FVG
bear es el máximo de los tres highs, y la R del pack va neta de fees).

## Las doce celdas (15m; costes gate: taker cinco + slip medio punto por lado, maker dos; funding apagado, declarado; run_id citado por línea)

Modo market (certificable - fills taker en la apertura siguiente):

- BTCUSDT `e61d0dda1c4f1705` - PF 0.859, net -72.55%, n 983, OOS PF 0.713, conc -13.6% -> FAIL
- ETHUSDT `0ebdca6b532f2025` - PF 0.875, net -67.25%, n 1010, OOS PF 0.861, conc -17.8% -> FAIL
- SOLUSDT `45ffecd2da31bb02` - PF 0.987, net -11.44%, n 895, OOS PF 0.797, conc -170.8% -> FAIL
- HYPEUSDT `f955da402137a517` - PF 1.014, net +2.12%, n 204, OOS PF 0.775, conc 519.5% -> FAIL
- SUIUSDT `00d2707b0dd74261` - PF 0.840, net -46.85%, n 483, OOS PF 0.653, conc -20.5% -> FAIL
- JUPUSDT `efaa844c8075c6e4` - PF 0.971, net -8.66%, n 427, OOS PF 0.839, conc -127.9% -> FAIL

Modo limit (entrada maker descansando dentro de la 15M FVG - **fill model maker_intrabar: NO certificable sobre barras OHLC segun la regla de la casa**; los numeros se registran como historia, no como evidencia):

- BTCUSDT `5e2e3e1ef9a7a9e4` - PF 0.905, net -39.00%, n 616, OOS PF 0.731, conc -33.9% -> FAIL
- ETHUSDT `96cffffa95971b6c` - PF 1.022, net +12.31%, n 630, OOS PF 0.927, conc 118.3% -> FAIL
- SOLUSDT `b30047899edc8cf3` - PF 0.886, net -40.63%, n 535, OOS PF 0.778, conc -31.9% -> FAIL
- HYPEUSDT `a45dcec797d8721e` - PF 1.004, net +0.40%, n 126, OOS PF 0.439, conc 2824.5% -> FAIL
- SUIUSDT `25fe2506aa724b78` - PF 0.832, net -33.87%, n 290, OOS PF 0.693, conc -31.0% -> FAIL
- JUPUSDT `d7cf9f2832cbb19c` - PF 1.006, net +0.97%, n 239, OOS PF 1.079, conc 1111.6% -> FAIL

## Por qué muere (medido dentro de los artefactos)

- **Costes**: el drag de coste cero a costes del repo es brutal con este
  ritmo de trading — ETH limit pasa de +204.15% a +12.31% (drag +191.84pp
  sobre seiscientos treinta trades), BTC market de +108.10% a -72.55%
  (drag +180.66pp). El coste medio medido por round trip: 5.8 bps en limit
  (maker) y 9.0 bps en market.
- **Ningún IC bootstrap propio excluye el cero** — el mejor (ETH limit)
  da [-12.44, +16.14], P de media menor o igual a cero 0.395.
- **Concentración**: JUP limit tiene un best-5 del 1111.6% del PnL y HYPE
  market del 519.5% — libros sostenidos por un puñado de trades.
- **OOS setenta-treinta**: el PF OOS de las celdas market cae a
  0.71-0.78 — la señal no sobrevive fuera de muestra ni en su mejor símbolo.
- **Paridad e invariante**: los doce artefactos carrying parity_ok=True
  (vector y evento de acuerdo trade a trade) y el gap de la identidad
  contable por debajo de un microdólar — los números son lo que los dos
  motores calculan, y lo que calculan no pasa.

## Notas de ejecución del porte

- La curva de equity del pack es por-trade (marcada en cada salida); el OOS
  setenta-treinta filtra por tiempo de entrada sobre el índice de barras y
  mide el retorno sobre la curva de trades desde la primera operación OOS —
  declarado en el artefacto.
- Funding apagado (pack solo-klines, declarado): con holds de hasta
  noventa y seis barras de 15m el drag de funding real seria pequeno pero
  no cero; declarado, no estimado.

## Próximo paso según doctrina

Ninguna re-corrida lo revive. El modo limit es la única pinta de vida y no
es certificable sobre barras OHLC — su único camino legitimo es un registro
forward en papel (o una resolución de fills a 1m), con la puerta del IC
bootstrap, que con estos PnL por trade no llega.
