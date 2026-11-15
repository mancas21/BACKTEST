# Top cien con estrategia al lado

La columna Estrategia trae la regla en lenguaje, la clave y la referencia de código; los parámetros exactos y datos están en el JSON.

| # | Estrategia (regla) | Mercado | Trades | Net % | PF | run_id |
|---:|---|---|---:|---:|---:|---|
| 1 | BOT-Strat: caja de pivotes cuarenta y nueve barras, rotura al cierre, entrada al siguiente open; stops y salidas parciales en múltiplos de R. | SPXUSDT 1h | 31 | 38.72 | 3.079 | `f2aa1050b118e54f` |
| 2 | QS-096: retest CHoCH tipo QS-033 pero solo cuando el percentil de ATR de quinientas barras está entre treinta y ochenta. | HYPEUSDT 1h | 68 | 32.87 | 2.609 | `5cdb10b47424023f` |
| 3 | cierre sobre el máximo de ciento sesenta y ocho barras; salida bajo el mínimo de setenta y dos; stop a dos y medio ATR. | BTCUSDT 1h | 161 | 367.97 | 2.545 | `b2527f9b2b8d7220` |
| 4 | desplazamiento con cuerpo dominante y hold del midpoint durante una a tres barras, con rotura de la consolidacion; trailing de dos ATR. | SUIUSDT 1h | 50 | 27.33 | 2.389 | `2f21db59610c9249` |
| 5 | ruptura Donchian con confirmación de flujo agresivo y tendencia HTF; stop ancho ATR. | QQQ 1d | 39 | 25.24 | 2.192 | `68c93ae390084b18` |
| 6 | momentum time-series con retorno ajustado por volatilidad y umbral de entrada/salida; pocas operaciones y stop ATR ancho. | XRPUSDT 1h | 173 | 174.39 | 1.755 | `db89577d5f9d9d34` |
| 7 | compresion de ocho barras dentro del tercio alto/bajo de un rango previo de sesenta y rotura de la consolidacion; objetivo al extremo del rango previo. | ETHUSDT 1h | 122 | 46.13 | 1.728 | `21f1495a22c44230` |
| 8 | regimen de volatilidad realizada que cruza hacia arriba tras estar bajo; ruptura Donchian de treinta barras; stop a dos ATR. | ETHUSDT 1h | 50 | 25.89 | 1.688 | `f3a22e459849e2f4` |
| 9 | SMQE v1.1: núcleo CVRMD con divergencia alcista/bajista, cercanía a banda VWAP, pendiente CVD y filtro RSI; entradas y flips con cooldown, TP parciales y stop congelado. | SUIUSDT 1h | 53 | 14.65 | 1.675 | `628003fe77ab72f8` |
| 10 | cierre sobre Keltner veinte con banda dos y RSI catorce sobre sesenta; salida bajo EMA veinte; stop a dos ATR. | HYPEUSDT 1h | 128 | 40.31 | 1.602 | `41826481d4dfbdeb` |
| 11 | desplazamiento con cuerpo dominante y hold del midpoint durante una a tres barras, con rotura de la consolidacion; trailing de dos ATR. | ETHUSDT 1h | 57 | 14.79 | 1.597 | `48bbf8b6e6ada97f` |
| 12 | momentum time-series con retorno ajustado por volatilidad y umbral de entrada/salida; pocas operaciones y stop ATR ancho. | SOLUSDT 1h | 176 | 70.79 | 1.590 | `ded7cca009e13445` |
| 13 | ruptura de noventa y seis barras con ATR expandiendo y nivel de ATR alto; trailing de dos y media ATR y salida por EMA veintiuno. | ETHUSDT 1h | 388 | 882.14 | 1.586 | `3aaf8d34f49f1187` |
| 14 | ruptura Donchian con confirmación de flujo agresivo y tendencia HTF; stop ancho ATR. | XRPUSDT 1h | 227 | 180.87 | 1.584 | `db89577d5f9d9d34` |
| 15 | squeeze Bollinger de veinte barras y dos desviaciones, banda en el decil bajo de doscientas; ruptura del squeeze; stop a dos ATR. | HYPEUSDT 1h | 121 | 62.55 | 1.569 | `5c2128e5190aa4b7` |
| 16 | QS-096: retest CHoCH tipo QS-033 pero solo cuando el percentil de ATR de quinientas barras está entre treinta y ochenta. | SUIUSDT 1h | 148 | 29.82 | 1.497 | `11de44fd24c5ecac` |
| 17 | reversión domingo-lunes: domingo por la noche tras caída de más de un ATR desde la apertura del domingo y cierre el lunes por la noche/martes; stop a dos ATR. | ETHUSDT 1h | 128 | 37.53 | 1.453 | `92416cc5f41137af` |
| 18 | ruptura Donchian de veinte barras solo si el regimen de mayor temporalidad sigue el mismo lado; stop a dos ATR. | ETHUSDT 1h | 118 | 43.44 | 1.448 | `e174928decd9b917` |
| 19 | bandas de deriva de flujo taker con alineación HTF y guardia anti-inversión de banda; entradas al cruzar bandas y salidas por inversión. | QQQ 1d | 81 | 24.18 | 1.427 | `68c93ae390084b18` |
| 20 | SMQE v1.1: núcleo CVRMD con divergencia alcista/bajista, cercanía a banda VWAP, pendiente CVD y filtro RSI; entradas y flips con cooldown, TP parciales y stop congelado. | SOLUSDT 1h | 84 | 14.99 | 1.424 | `2bdc4afdf0d51f93` |
| 21 | pullback de tendencia HTF con RSI dos extremo; entrada al snap-back y salida por RSI, ATR o tiempo. | QQQ 1d | 99 | 11.43 | 1.411 | `68c93ae390084b18` |
| 22 | compresion ATR relativa frente a su ATR lento; vela de expansion con cierre en el tercio superior/inferior; stop a dos ATR. | BTCUSDT 1h | 85 | 22.64 | 1.402 | `25a0d385da7c5026` |
| 23 | ruptura Donchian de veinte barras con volumen mayor que el doble de su media de veinte; stop a dos ATR. | SOLUSDT 1h | 240 | 53.30 | 1.399 | `829abb112d6b3564` |
| 24 | cambio de caracter confirmado: ruptura del ultimo máximo/mínimo con volumen y ADX acotado, retest del nivel roto y continuacion; stop desde el swing previo. | SOLUSDT 1h | 180 | 32.07 | 1.399 | `53c79260fac01e20` |
| 25 | compresion ATR relativa frente a su ATR lento; vela de expansion con cierre en el tercio superior/inferior; stop a dos ATR. | SOLUSDT 1h | 51 | 16.66 | 1.392 | `7a7bd74f7f402e07` |
| 26 | ruptura Donchian de veinte barras seguida de retest del nivel roto dentro de diez barras y continuacion del lado roto; stop cerca del nivel tensionado. | SOLUSDT 1h | 351 | 78.05 | 1.389 | `e2cf2e0aae688a2c` |
| 27 | cierre sobre el máximo Donchian de cincuenta y cinco; salida bajo el mínimo Donchian de veinte; stop a tres ATR. | BTCUSDT 1h | 430 | 113.71 | 1.371 | `758e39eb9d13681a` |
| 28 | cruce EMA veinte / EMA cincuenta; cierre contra el cruce contrario; stop a tres ATR. | ETHUSDT 1h | 1134 | 444.70 | 1.358 | `4605b2b4d2607fc0` |
| 29 | ruptura Donchian de veinte barras solo si el regimen de mayor temporalidad sigue el mismo lado; stop a dos ATR. | SOLUSDT 1h | 138 | 23.70 | 1.347 | `00915ec321531a5d` |
| 30 | barrido de liquidez en nivel HTF más FVG de tres barras; entrada al tocar el FVG y cerrar de vuelta por su midpoint; stop tras el extremo barrido. | SOLUSDT 15m | 61 | 29.67 | 1.332 | `280e88028bd44e31` |
| 31 | QS-096: retest CHoCH tipo QS-033 pero solo cuando el percentil de ATR de quinientas barras está entre treinta y ochenta. | DOGEUSDT 1h | 241 | 31.16 | 1.318 | `1b36fe43e7cee680` |
| 32 | alineacion estructural multi-temporal: ruptura LTF del ultimo pivote solo si la estructura HTF apunta al mismo lado; stop desde el pivote contrario. | ETHUSDT 1h | 210 | 29.03 | 1.307 | `d762dd6c2495298f` |
| 33 | gap de fin de semana superior o inferior al uno por ciento; fade hacia el cierre del viernes, stop a una y media veces el gap. | BTCUSDT 1h | 60 | 26.68 | 1.303 | `1b13cbd18f8b00eb` |
| 34 | cambio de caracter confirmado: ruptura del ultimo máximo/mínimo con volumen y ADX acotado, retest del nivel roto y continuacion; stop desde el swing previo. | HYPEUSDT 1h | 117 | 11.86 | 1.298 | `61a839cefd3fdfab` |
| 35 | cambio de caracter confirmado: ruptura del ultimo máximo/mínimo con volumen y ADX acotado, retest del nivel roto y continuacion; stop desde el swing previo. | SUIUSDT 1h | 155 | 17.68 | 1.290 | `ea9d8bbda925b7ef` |
| 36 | barrido de rango viejo con dos toques en cada extremo y giro de vuelta dentro; objetivo al midpoint; stop tras el extremo barrido. | SOLUSDT 1h | 137 | 35.94 | 1.290 | `3fe037783fb12904` |
| 37 | QS-096: retest CHoCH tipo QS-033 pero solo cuando el percentil de ATR de quinientas barras está entre treinta y ochenta. | XRPUSDT 1h | 286 | 24.74 | 1.275 | `c4ad405b3c428ce5` |
| 38 | QS-096: retest CHoCH tipo QS-033 pero solo cuando el percentil de ATR de quinientas barras está entre treinta y ochenta. | SOLUSDT 1h | 269 | 27.23 | 1.273 | `2b7bc76f88084065` |
| 39 | cruce EMA veinte / cincuenta solo en horas catorce a diecisiete UTC; stop a dos ATR. | JUPUSDT 1h | 97 | 15.82 | 1.265 | `19e3ac2f0e90cad2` |
| 40 | pendiente de regresión de cincuenta barras que cruza cero; stop a dos ATR. | SOLUSDT 1h | 1096 | 354.99 | 1.258 | `f4e6f60d74c61383` |
| 41 | agotamiento tras cinco cierres del mismo signo y deceleracion con volumen cayente; entrada contra la racha al primer cierre opuesto. | SUIUSDT 5m | 33 | 5.40 | 1.253 | `73a2506159a85ad4` |
| 42 | rango mayor que dos ATR y cierre en la parte alta de la barra; stop por el cuerpo inferior y salida bajo el mínimo previo. | SOLUSDT 1h | 533 | 40.94 | 1.249 | `14bf1f0ec9b63682` |
| 43 | regimen de volatilidad realizada que cruza hacia arriba tras estar bajo; ruptura Donchian de treinta barras; stop a dos ATR. | SUIUSDT 1h | 48 | 7.75 | 1.243 | `bc05fce85d442e0c` |
| 44 | QS-097: ruptura Donchian de veinte barras en el activo operado solo si BTC y ETH están sobre su EMA cincuenta y al menos dos de los otros están sobre la suya. | ETHUSDT 1h | 306 | 25.99 | 1.234 | `c07e26b442263679` |
| 45 | ruptura Donchian de veinte barras con volumen mayor que el doble de su media de veinte; stop a dos ATR. | SUIUSDT 1h | 226 | 18.80 | 1.226 | `de77151964899879` |
| 46 | momentum time-series con retorno ajustado por volatilidad y umbral de entrada/salida; pocas operaciones y stop ATR ancho. | ETHUSDT 1h | 181 | 26.16 | 1.224 | `2e823fa306c91366` |
| 47 | squeeze Bollinger de veinte barras y dos desviaciones, banda en el decil bajo de doscientas; ruptura del squeeze; stop a dos ATR. | SOLUSDT 1h | 177 | 20.59 | 1.220 | `1531130936c7e113` |
| 48 | RSI catorce en SOL/USDC: entrada a la baja cuando RSI cruza bajo treinta y salida cuando vuelve sobre setenta; ejecución al siguiente open. | SOLUSDC 1h | 60 | 7.56 | 1.217 | `dcf66a3eb320e7a7` |
| 49 | ruptura de noventa y seis barras con ATR expandiendo y nivel de ATR alto; trailing de dos y media ATR y salida por EMA veintiuno. | XRPUSDT 1h | 361 | 331.12 | 1.209 | `0d78d36f19b8f49f` |
| 50 | regimen de volatilidad realizada que cruza hacia arriba tras estar bajo; ruptura Donchian de treinta barras; stop a dos ATR. | ETHUSDT 5m | 161 | 24.95 | 1.207 | `c403a294e46f89e5` |
| 51 | QS-097: ruptura Donchian de veinte barras en el activo operado solo si BTC y ETH están sobre su EMA cincuenta y al menos dos de los otros están sobre la suya. | SUIUSDT 1h | 295 | 26.08 | 1.192 | `69d9e9bb940152d6` |
| 52 | ruptura Donchian con confirmación de flujo agresivo y tendencia HTF; stop ancho ATR. | SUIUSDT 1h | 240 | 34.75 | 1.191 | `c1f3df39b37c1d2b` |
| 53 | liberación de squeeze Bollinger/Keltner con momentum y acuerdo de flujo; objetivo a múltiplos ATR. | XRPUSDT 1h | 196 | 28.40 | 1.188 | `db89577d5f9d9d34` |
| 54 | QS-097: ruptura Donchian de veinte barras en el activo operado solo si BTC y ETH están sobre su EMA cincuenta y al menos dos de los otros están sobre la suya. | HYPEUSDT 1h | 162 | 10.55 | 1.181 | `6f5ec1d20c40a815` |
| 55 | QS-096: retest CHoCH tipo QS-033 pero solo cuando el percentil de ATR de quinientas barras está entre treinta y ochenta. | ETHUSDT 1h | 309 | 16.77 | 1.176 | `c8a00fe20ff4ad6f` |
| 56 | QS-096: retest CHoCH tipo QS-033 pero solo cuando el percentil de ATR de quinientas barras está entre treinta y ochenta. | NEARUSDT 1h | 279 | 20.69 | 1.173 | `da9f1b3771077f89` |
| 57 | ruptura Donchian de veinte barras con volumen mayor que el doble de su media de veinte; stop a dos ATR. | HYPEUSDT 1h | 144 | 11.49 | 1.171 | `ce6ac1a096d49d4f` |
| 58 | regimen de volatilidad realizada que cruza hacia arriba tras estar bajo; ruptura Donchian de treinta barras; stop a dos ATR. | SOLUSDT 1h | 44 | 3.64 | 1.160 | `172c2168dd0bb06e` |
| 59 | ds1: momentum time-series de ciento sesenta y ocho horas con objetivo de volatilidad; el tamaño se deriva del equity y cambia con la señal. | HYPEUSDT 1h | 407 | 14.40 | 1.150 | `88bc7c612612f5f8` |
| 60 | ruptura Donchian con confirmación de flujo agresivo y tendencia HTF; stop ancho ATR. | ETHUSDT 1h | 249 | 28.02 | 1.150 | `2e823fa306c91366` |
| 61 | alineacion estructural multi-temporal: ruptura LTF del ultimo pivote solo si la estructura HTF apunta al mismo lado; stop desde el pivote contrario. | SUIUSDT 1h | 234 | 13.94 | 1.136 | `cae06c339ca696d7` |
| 62 | momentum time-series con retorno ajustado por volatilidad y umbral de entrada/salida; pocas operaciones y stop ATR ancho. | SUIUSDT 1h | 167 | 12.99 | 1.133 | `c1f3df39b37c1d2b` |
| 63 | momentum time-series con retorno ajustado por volatilidad y umbral de entrada/salida; pocas operaciones y stop ATR ancho. | HYPEUSDT 1h | 121 | 9.30 | 1.130 | `44f6ae02bb2fe93c` |
| 64 | fade de funding extremo con rollover tras EMA; entrada contra el posicionamiento, TP amplio ATR y holding máximo. | ETHUSDT 1h | 34 | 2.71 | 1.126 | `2e823fa306c91366` |
| 65 | QS-096: retest CHoCH tipo QS-033 pero solo cuando el percentil de ATR de quinientas barras está entre treinta y ochenta. | NVDAUSDT 15m | 85 | 4.36 | 1.116 | `9a869c49aaa083d6` |
| 66 | ruptura Donchian con confirmación de flujo agresivo y tendencia HTF; stop ancho ATR. | HYPEUSDT 1h | 177 | 11.96 | 1.109 | `44f6ae02bb2fe93c` |
| 67 | ds7: RSI dos estilo Connors con filtro de tendencia EMA doscientas; entradas por extremo, salidas por retorno a la media. | SPXUSDT 1h | 296 | 44.97 | 1.108 | `b898dfed4e6f2395` |
| 68 | ruptura Donchian de veinte barras con volumen mayor que el doble de su media de veinte; stop a dos ATR. | ETHUSDT 1h | 277 | 13.37 | 1.106 | `cdbed9c0749e2dee` |
| 69 | ruptura Donchian de veinte barras solo si el regimen de mayor temporalidad sigue el mismo lado; stop a dos ATR. | SOLUSDT 15m | 595 | 23.57 | 1.097 | `7b0022b3bbf0a0f7` |
| 70 | ruptura Donchian con confirmación de flujo agresivo y tendencia HTF; stop ancho ATR. | JUPUSDT 1h | 243 | 15.54 | 1.096 | `f911813458f9a2ec` |
| 71 | barrido de liquidez en nivel HTF más FVG de tres barras; entrada al tocar el FVG y cerrar de vuelta por su midpoint; stop tras el extremo barrido. | XRPUSDT 1h | 172 | 25.50 | 1.094 | `52677740cad35881` |
| 72 | liberación de squeeze Bollinger/Keltner con momentum y acuerdo de flujo; objetivo a múltiplos ATR. | HYPEUSDT 1h | 111 | 7.14 | 1.092 | `44f6ae02bb2fe93c` |
| 73 | ruptura Donchian de veinte barras solo si el regimen de mayor temporalidad sigue el mismo lado; stop a dos ATR. | SUIUSDT 1h | 134 | 4.99 | 1.091 | `d4ba13a9ab12605d` |
| 74 | ruptura Donchian de veinte barras solo si el regimen de mayor temporalidad sigue el mismo lado; stop a dos ATR. | HYPEUSDT 15m | 221 | 7.86 | 1.089 | `3f3e22e27e26315b` |
| 75 | desviación intradía de VWAP por debajo de menos dos sigmas con rechazo alcista; retorno a VWAP y stop a tres y medio sigmas. | SOLUSDT 15m | 17850 | 405901.02 | 1.077 | `44a23ab194b621be` |
| 76 | Heikin-Ashi: tres velas verdes sin mecha inferior consecutivas; salida en la primera roja; stop a dos y medio ATR. | SUIUSDT 4h | 110 | 16.09 | 1.077 | `1300b325a1544451` |
| 77 | continuacion de estructura: pullback del treinta y ocho al sesenta y dos por ciento de la ultima pierna con estructura HH/HL o LH/LL; objetivo al extremo previo. | SUIUSDT 1h | 199 | 8.78 | 1.077 | `ccff24de952452f7` |
| 78 | squeeze por ancho Bollinger en el decil bajo, ruptura de veinte barras con ROC diez a favor; salida si el rank supera sesenta. | SOLUSDT 1h | 684 | 89.98 | 1.076 | `bd9100c8bd70d366` |
| 79 | ruptura Donchian de veinte barras solo si el regimen de mayor temporalidad sigue el mismo lado; stop a dos ATR. | SUIUSDT 5m | 431 | 19.54 | 1.075 | `e63b3a81499c0c76` |
| 80 | ruptura fallida de veinte barras seguida, en una a tres barras, de cierre de vuelta dentro del nivel roto; objetivo al midpoint y stop tras el extremo fallido. | ETHUSDT 1h | 403 | 14.59 | 1.070 | `a204b14dac5f7e47` |
| 81 | regimen de volatilidad realizada que cruza hacia arriba tras estar bajo; ruptura Donchian de treinta barras; stop a dos ATR. | HYPEUSDT 15m | 108 | 3.13 | 1.065 | `d2f68e91ecb3a767` |
| 82 | ruptura de noventa y seis barras con ATR expandiendo y nivel de ATR alto; trailing de dos y media ATR y salida por EMA veintiuno. | BTCUSDT 1h | 434 | 33.91 | 1.063 | `6aa3e550b74655a9` |
| 83 | compresion de ocho barras dentro del tercio alto/bajo de un rango previo de sesenta y rotura de la consolidacion; objetivo al extremo del rango previo. | ETHUSDT 15m | 359 | 8.60 | 1.062 | `d16cf5428d8ca01d` |
| 84 | CVRMD: VWAP de sesión más una desviación, pendiente CVD, RSI catorce y divergencia MACD en pivotes; stop ATR y salidas parciales en VWAP y dos R. | XRPUSDT 1h | 99 | 2.62 | 1.060 | `45ccfbbb288a7ea7` |
| 85 | rechazo de zona de soporte/resistencia: dos pivotes cercanos, mecha de rechazo y cierre de vuelta dentro; objetivo a dos veces el riesgo. | SUIUSDT 1h | 197 | 4.30 | 1.060 | `7efc035fd52a8911` |
| 86 | alineacion estructural multi-temporal: ruptura LTF del ultimo pivote solo si la estructura HTF apunta al mismo lado; stop desde el pivote contrario. | HYPEUSDT 1h | 149 | 2.24 | 1.058 | `cfaf023ce80d3ed8` |
| 87 | liberación de squeeze Bollinger/Keltner con momentum y acuerdo de flujo; objetivo a múltiplos ATR. | JUPUSDT 1h | 172 | 6.77 | 1.056 | `de5e832e962d8d9f` |
| 88 | ruptura fallida de veinte barras seguida, en una a tres barras, de cierre de vuelta dentro del nivel roto; objetivo al midpoint y stop tras el extremo fallido. | BTCUSDT 5m | 248 | 5.81 | 1.055 | `6738cdaccbb558de` |
| 89 | desplazamiento con cuerpo dominante y hold del midpoint durante una a tres barras, con rotura de la consolidacion; trailing de dos ATR. | SUIUSDT 15m | 165 | 3.98 | 1.052 | `1681d304142e1dcd` |
| 90 | ruptura del ultimo pivote confirmado con distancia minima de media ATR; stop entre uno y tres ATR; salida al cruzar el pivote contrario. | SOLUSDT 1h | 384 | 7.28 | 1.052 | `1cc6f7489bcaa85a` |
| 91 | ruptura Donchian con confirmación de flujo agresivo y tendencia HTF; stop ancho ATR. | SOLUSDT 1h | 269 | 9.94 | 1.051 | `ded7cca009e13445` |
| 92 | QS-096: retest CHoCH tipo QS-033 pero solo cuando el percentil de ATR de quinientas barras está entre treinta y ochenta. | AVAXUSDT 1h | 255 | 4.51 | 1.049 | `c29b5798f9f69df7` |
| 93 | TTM squeeze: Bollinger dentro de Keltner y momentum hl2 cruzando cero; stop a dos ATR. | XRPUSDT 1h | 3396 | 488.30 | 1.048 | `ea426bb3fb821132` |
| 94 | barrido de liquidez en nivel HTF más FVG de tres barras; entrada al tocar el FVG y cerrar de vuelta por su midpoint; stop tras el extremo barrido. | SOLUSDT 1h | 36 | 4.33 | 1.046 | `ddb39cfadb02ce59` |
| 95 | bandas de deriva de flujo taker con alineación HTF y guardia anti-inversión de banda; entradas al cruzar bandas y salidas por inversión. | SUIUSDT 1h | 292 | 8.76 | 1.045 | `c1f3df39b37c1d2b` |
| 96 | fade de funding extremo con rollover tras EMA; entrada contra el posicionamiento, TP amplio ATR y holding máximo. | SUIUSDT 1h | 40 | 0.99 | 1.036 | `c1f3df39b37c1d2b` |
| 97 | ruptura Donchian de veinte barras con volumen mayor que el doble de su media de veinte; stop a dos ATR. | SUIUSDT 5m | 311 | 5.91 | 1.035 | `177a598c398080b5` |
| 98 | ruptura Donchian de veinte barras con volumen mayor que el doble de su media de veinte; stop a dos ATR. | SUIUSDT 15m | 510 | 5.78 | 1.030 | `21f78ce657de0945` |
| 99 | ruptura fallida de veinte barras seguida, en una a tres barras, de cierre de vuelta dentro del nivel roto; objetivo al midpoint y stop tras el extremo fallido. | SUIUSDT 1h | 152 | 2.62 | 1.029 | `f12bf23e1042d8c9` |
| 100 | compresion de ocho barras dentro del tercio alto/bajo de un rango previo de sesenta y rotura de la consolidacion; objetivo al extremo del rango previo. | SUIUSDT 1h | 145 | 1.41 | 1.029 | `694b8e7e1b64e88c` |
