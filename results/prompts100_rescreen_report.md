# Re-screen de los cien prompts del pack con el harness del repo

- generated: `2026-11-21`
- spec congelado antes de la primera corrida: `results/prompts100_rescreen_pre_registration.md`
- codigo del pack copiado verbatim a `code/prompts100/` con manifiesto sha256; motor del repo: `code/p100_screen_engine.py`; adapter `p100screen`
- paridad: `code/_prompts100_parity.py` (trades y metricas identicos al motor del pack); respuestas conocidas: `code/_prompts100_audit.py` (ambas direcciones)
- costes: **el coste resuelto por simbolo** (maximo entre los 11 bps RT por defecto y el RT MEDIDO del cost model `results/cost_model_2026-10-25.json`: fee 5 bps, slip rt/2-5; los libros multi-pierna cobran el maximo de sus piernas) y **funding cobrado en los settlements reales ANTES de los stops intrabar** (fix N11 2026-11-21); el invariante contable se aserta dentro de cada artefacto; el coste resuelto viaja MEDIDO en cada artefacto (`cost_bp_roundtrip`, `cost_source`)

## Veredicto

De los noventa prompts medidos, **cuatro** limpian la criba sobre DEV y **cero** superan el veredicto completo sobre OOS (uno de los supervisivientes es pares y no es certificables: su nocional implicito no es sostenible). La razon principal no es el modelo: es el coste. El pack original corria a 2.2 bps round trip (su constante es 0.000055, o sea 0.55 bps por lado, diez veces menos de lo que documenta) y sin funding; el repo cobra 11 bps y el funding real. Ese salto es lo que separa las dos cribas.


## Lo que la criba del pack dejo fuera y esta no

| hallazgo | como se midio |
|---|---|
| el pack ordena los cien prompts por su **propio** OOS Profit Factor, asi que ese tramo deja de ser una estimacion fuera de muestra | aqui la seleccion se hace SOLO sobre DEV, hay un mes de purga sin operar, y el veredicto se lee despues |
| el pack cobra 2.2 bps round trip (su constante es 0.000055, o sea 0.55 bps por lado, diez veces menos de lo que documenta) | el repo cobra 11 bps: el pack es cinco veces mas barato que el estandar de la casa |
| el pnl por trade del pack **no incluye la comision de entrada** (solo la carga en la caja), asi que su profit factor no es del todo ex-cost | aqui el pnl lleva las dos comisiones y el invariante contable cierra |
| el pack **descarta** el trade cuyo hueco de entrada ya atraviesa el stop ("setup invalido") | aqui ese trade se rellena al open: un hueco malo es un resultado malo, no un trade que no existio |
| el pack no cobra funding | aqui se cobra en los settlements reales, en las dos piernas |

## La criba (DEV) y el veredicto (OOS): un solo simbolo

| # | prompt | par | run_id DEV | n DEV | PF DEV | net DEV % | criba | run_id OOS | n OOS | PF OOS | net OOS % | veredicto |
|---|---|---|---|---:|---:|---:|---|---|---:|---:|---:|---|
| 57 | ETHUSDT 15m | `91b6021e5c31cb27` | 11 | 275.9425 | 1653.51 | tres de seis | `26101e53d3351f51` | 73 | 0 | -65.29 | INSUFICIENTE MUESTRA |
| 59 | SOLUSDT 1h | `910281e1f82b51c9` | 9 | 70.7753 | 441.53 | tres de seis | `8d1760ff1e388289` | 30 | 0.3062 | -18.75 | INSUFICIENTE MUESTRA |
| 75 | HYPEUSDT 1h | `a334d65d2105fcf6` | 2 | 7.4782 | 5.31 | tres de seis | `9cf8123eaf066990` | 9 | 7.0177 | 45.36 | INSUFICIENTE MUESTRA |
| 63 | BTCUSDT 15m | `4b085c7394fff666` | 32 | 6.7655 | 102.21 | cuatro de seis | `3906d30c550c8acd` | 32 | 0.2782 | -25.06 | no pasa la criba |
| 23 | SUIUSDT 15m | `2ce6ed990f5f3e16` | 69 | 6.3560 | 247.69 | cuatro de seis | `015ba74bb76e54d7` | 68 | 0.1294 | -46.74 | no pasa la criba |
| 44 | BTCUSDT 1h | `f4cc570d6b8b8199` | 136 | 2.2929 | 253.78 | seis de seis | `2e739e5705368a7f` | 22 | 1.3816 | 5.94 | KILLED (veredicto OOS) |
| 64 | ETHUSDT 1h | `b47ea79ad5bc3369` | 42 | 1.8551 | 28.87 | cuatro de seis | `e8943952c10101e5` | 15 | 0 | -15.78 | no pasa la criba |
| 29 | HYPEUSDT 15m | `458765c511bcb8ba` | 7 | 1.5191 | 0.73 | tres de seis | `368e87fb2c8c1998` | 36 | 2.8990 | 53.91 | INSUFICIENTE MUESTRA |
| 73 | ETHUSDT 1h | `d432a4a46f8594e3` | 106 | 1.4695 | 36.15 | cuatro de seis | `1f2840f856eb395d` | 19 | 2.0567 | 8.60 | no pasa la criba |
| 22 | HYPEUSDT 1h | `2dbf505743a1a2d1` | 28 | 1.3719 | 3.41 | tres de seis | `4aa4f5e848ab041d` | 95 | 0.8959 | -4.51 | INSUFICIENTE MUESTRA |
| 28 | BTCUSDT 1h | `bb1b90c42f6bfd4b` | 366 | 1.3360 | 73.28 | seis de seis | `8cbdb2c8ddd2c132` | 63 | 0.7882 | -8.22 | KILLED (veredicto OOS) |
| 68 | SOLUSDT 1h | `ac9a7eda6f9977ef` | 263 | 1.3253 | 55.03 | cinco de seis | `25c52b873cfe35c8` | 52 | 0.7832 | -7 | no pasa la criba |
| 45 | ETHUSDT 1h | `d889667a3e014163` | 622 | 1.2748 | 264.49 | cinco de seis | `6c285f1d61e2a971` | 124 | 1.0137 | 0.77 | no pasa la criba |
| 26 | ETHUSDT 1h | `c702db037672f1fe` | 942 | 1.2622 | 319.09 | seis de seis | `7d70052d9015b588` | 183 | 1.0348 | 3.17 | KILLED (veredicto OOS) |
| 72 | BTCUSDT 1h | `f7338649fb98ba15` | 317 | 1.1512 | 32.78 | cuatro de seis | `f2e2de19bb4d3ee8` | 53 | 0.6265 | -13.18 | no pasa la criba |
| 52 | BTCUSDT 15m | `2b557b08604aaa1a` | 877 | 1.1320 | 393.33 | cuatro de seis | `7248c262c49519f5` | 179 | 1.0705 | 13.86 | no pasa la criba |
| 60 | HYPEUSDT 1h | `0b67a162a6f8761f` | 50 | 1.0918 | 1.48 | tres de seis | `aa0b830656c63f37` | 141 | 1.3490 | 23.10 | no pasa la criba |
| 34 | SOLUSDT 1h | `56cbab9538f5d9ba` | 1561 | 1.0849 | 118.68 | tres de seis | `f78f1b84f35b7517` | 335 | 0.9492 | -10.27 | no pasa la criba |
| 21 | SOLUSDT 1h | `41e823f190bfcf93` | 27 | 0.9948 | -0.34 | cero de seis | `e360a8f36430ec2a` | 8 | 1.5191 | 2.69 | INSUFICIENTE MUESTRA |
| 4 | HYPEUSDT 1h | `65a53548135e936b` | 127 | 0.9900 | -1.12 | dos de seis | `955e1f4d8460e396` | 386 | 0.7735 | -34.57 | no pasa la criba |
| 69 | HYPEUSDT 15m | `c4bb70ef1c40451e` | 61 | 0.9834 | -0.59 | dos de seis | `b372e2ab78295e7c` | 151 | 0.7569 | -22.75 | no pasa la criba |
| 47 | BTCUSDT 5m | `b885565f89e9967c` | 7900 | 0.9657 | -100 | uno de seis | `8df068dfdaf94747` | 1627 | 0.6031 | -99.98 | no pasa la criba |
| 53 | SOLUSDT 5m | `d9b5110c5e5fd978` | 3322 | 0.9501 | -99.69 | uno de seis | `34c047a4d3f84939` | 711 | 0.5416 | -96.30 | no pasa la criba |
| 7 | BTCUSDT 1h | `02f818e12eb73444` | 1083 | 0.8985 | -44.65 | uno de seis | `a22cf9164477e378` | 138 | 0.6115 | -20.54 | no pasa la criba |
| 10 | HYPEUSDT 15m | `aa454455a606a728` | 213 | 0.8981 | -6.49 | uno de seis | `084ffe840c163c45` | 699 | 0.8207 | -30.81 | no pasa la criba |
| 11 | SUIUSDT 1h | `a165a9717d1d4343` | 171 | 0.8957 | -6.23 | uno de seis | `8350f23263050180` | 79 | 0.8983 | -2.77 | no pasa la criba |
| 16 | HYPEUSDT 5m | `c49838e428eaff0a` | 759 | 0.8915 | -57.43 | uno de seis | `645b1ae791a1ff6d` | 1991 | 0.8328 | -98.04 | no pasa la criba |
| 76 | SUIUSDT 5m | `604fb1b8b551cd82` | 23 | 0.8911 | -1.43 | cero de seis | `c196206c2d44c369` | 18 | 0.8933 | -1.83 | INSUFICIENTE MUESTRA |
| 14 | ETHUSDT 1h | `ce6b6b44ec5956f6` | 742 | 0.8831 | -41.69 | uno de seis | `b3e269d886694c29` | 106 | 0.7247 | -17.63 | no pasa la criba |
| 40 | SOLUSDT 5m | `3ac59bff618e2531` | 26449 | 0.8794 | -100 | uno de seis | `b3fb4dbf5729e09e` | 5739 | 0.6457 | -100 | no pasa la criba |
| 33 | BTCUSDT 15m | `1449219c6872fce3` | 7246 | 0.8318 | -100 | uno de seis | `6c44cfbc736b37fd` | 1211 | 0.5479 | -96.36 | no pasa la criba |
| 39 | ETHUSDT 15m | `ef2f4f932070e462` | 5735 | 0.8315 | -99.99 | uno de seis | `5ebf6fd995bfae7b` | 1019 | 0.6361 | -91.49 | no pasa la criba |
| 1 | SOLUSDT 1h | `0b698a09f94d69e4` | 514 | 0.8165 | -55.42 | uno de seis | `7625b8c7512d01d2` | 123 | 0.8822 | -9.76 | no pasa la criba |
| 30 | SUIUSDT 1h | `1623f411a785cb00` | 339 | 0.8142 | -26.56 | uno de seis | `c24f2ac0612b4f87` | 108 | 0.8996 | -5.87 | no pasa la criba |
| 37 | JUPUSDT 1h | `5cd2510ea5cb03f5` | 1374 | 0.8098 | -68.62 | uno de seis | `49e50f46b9ce0be0` | 805 | 0.9064 | -27.07 | no pasa la criba |
| 74 | SOLUSDT 15m | `cc9ecbe8a1948abf` | 1836 | 0.7985 | -84.14 | uno de seis | `a22284ab9b844d29` | 373 | 0.6550 | -49.98 | no pasa la criba |
| 15 | SOLUSDT 15m | `983913dfa9677572` | 5566 | 0.7955 | -99.99 | uno de seis | `525c173e4dd3eabd` | 1143 | 0.7207 | -91.74 | no pasa la criba |
| 80 | SOLUSDT 5m | `32deb4cc8d5f0da8` | 1829 | 0.7940 | -99.19 | uno de seis | `c048b3bdab2ee0ef` | 361 | 0.4574 | -77.85 | no pasa la criba |
| 55 | SUIUSDT 15m | `64a81d3d05ff20d7` | 1339 | 0.7581 | -84.54 | uno de seis | `8c10cacc40be2bf7` | 503 | 0.9361 | -23.26 | no pasa la criba |
| 5 | SUIUSDT 15m | `8d25e05ca089925d` | 3194 | 0.7446 | -99.45 | uno de seis | `29c6f086fc7a6d5e` | 1297 | 0.7271 | -91.55 | no pasa la criba |
| 6 | JUPUSDT 1h | `e0cbe87de5ae56e9` | 421 | 0.7419 | -35.28 | uno de seis | `c46ac2b95badd0e6` | 249 | 0.8168 | -14.81 | no pasa la criba |
| 48 | HYPEUSDT 15m | `336ee47b29667af7` | 1661 | 0.7356 | -86.74 | uno de seis | `2a07db0d3b6f3d68` | 5152 | 0.6636 | -99.99 | no pasa la criba |
| 8 | ETHUSDT 15m | `6252aaff76ab50f6` | 5474 | 0.7269 | -100 | uno de seis | `c651866e0aea6a91` | 1034 | 0.6487 | -91.76 | no pasa la criba |
| 24 | JUPUSDT 1h | `9f9cb59d1fe9113e` | 349 | 0.7243 | -44.19 | uno de seis | `f83fe01a2794a3b7` | 174 | 0.8818 | -10 | no pasa la criba |
| 9 | SOLUSDT 5m | `80c10db45d82f265` | 9420 | 0.7149 | -100 | uno de seis | `f4b9045d59db7ee8` | 2036 | 0.5960 | -99.98 | no pasa la criba |
| 36 | SUIUSDT 5m | `77cc3b26a4cc9679` | 2295 | 0.6884 | -97.56 | uno de seis | `320450aca1a3131a` | 991 | 0.5995 | -98.57 | no pasa la criba |
| 20 | ETHUSDT 5m | `8dad77e5e0cad65e` | 8856 | 0.6556 | -100 | uno de seis | `b12dcd1a491d768b` | 1677 | 0.5990 | -99.87 | no pasa la criba |
| 71 | JUPUSDT 1h | `771b358e1cc18893` | 62 | 0.6538 | -16.36 | uno de seis | `796513b7ca26964f` | 43 | 1.0598 | 2.01 | no pasa la criba |
| 43 | JUPUSDT 5m | `fb4879770d479c8c` | 4708 | 0.6348 | -100 | uno de seis | `465c74fe1b927451` | 3005 | 0.2704 | -100 | no pasa la criba |
| 50 | JUPUSDT 15m | `b7ab1f14f884573d` | 12452 | 0.6347 | -100 | uno de seis | `8db108c01b991fe9` | 7260 | 0.4684 | -100 | no pasa la criba |
| 25 | BTCUSDT 1h | `77218420c1ccba79` | 1213 | 0.6308 | -84.50 | uno de seis | `1600af4caf6f6985` | 208 | 0.5856 | -31.11 | no pasa la criba |
| 65 | SOLUSDT 15m | `8bbb420535a65216` | 1729 | 0.6295 | -88.09 | uno de seis | `1c510cdf0c142738` | 291 | 0.4012 | -44.10 | no pasa la criba |
| 18 | JUPUSDT 5m | `d7b2874539f17501` | 3029 | 0.6153 | -100 | uno de seis | `c08fcd81166b9f33` | 2143 | 0.5954 | -99.98 | no pasa la criba |
| 17 | SUIUSDT 5m | `64422e6e71a8a835` | 1603 | 0.6084 | -98.87 | uno de seis | `f6a4c7216e3ff1f3` | 561 | 0.6112 | -88.06 | no pasa la criba |
| 70 | SUIUSDT 15m | `fa0112fb96e59f15` | 1176 | 0.6081 | -93.61 | uno de seis | `8ee5ef9e9c90613d` | 536 | 0.5904 | -75.13 | no pasa la criba |
| 79 | ETHUSDT 5m | `187178b1e149c1e2` | 13845 | 0.5842 | -100 | uno de seis | `67f1e631bdb3373d` | 2355 | 0.4130 | -100 | no pasa la criba |
| 51 | ETHUSDT 5m | `724ee2ca366040a8` | 11986 | 0.5634 | -100 | uno de seis | `7b0db7adb5544306` | 2022 | 0.4673 | -99.99 | no pasa la criba |
| 12 | JUPUSDT 15m | `4444d607d5f06057` | 99 | 0.5467 | -27.27 | uno de seis | `6e4ea69ee120f9d7` | 173 | 0.6802 | -29.86 | no pasa la criba |
| 42 | SUIUSDT 15m | `471953849be7056c` | 7526 | 0.5423 | -99.96 | uno de seis | `fbb184898b6c63d1` | 3335 | 0.4810 | -99.65 | no pasa la criba |
| 66 | BTCUSDT 15m | `6558a70f85513e27` | 3736 | 0.5317 | -100 | uno de seis | `78123c9b18a0857a` | 600 | 0.4690 | -93.35 | no pasa la criba |
| 2 | BTCUSDT 15m | `6770df7c24da9538` | 4393 | 0.5223 | -100 | uno de seis | `a5ea8bd76bf61205` | 814 | 0.6174 | -91.89 | no pasa la criba |
| 13 | BTCUSDT 5m | `7e8730d2887390ea` | 3220 | 0.5217 | -100 | uno de seis | `6693be56f8a60fa5` | 664 | 0.5230 | -97.58 | no pasa la criba |
| 38 | BTCUSDT 5m | `1296f611bae1dab9` | 12049 | 0.5140 | -100 | uno de seis | `582478e524b279f8` | 1951 | 0.2611 | -100 | no pasa la criba |
| 61 | SUIUSDT 5m | `aa26d08b236ce98d` | 870 | 0.4799 | -98.83 | uno de seis | `e1fd9260ccc5cc37` | 354 | 0.4005 | -89.37 | no pasa la criba |
| 62 | JUPUSDT 5m | `ac7258954db46a09` | 1425 | 0.4788 | -99.86 | uno de seis | `05764eb4ad11a485` | 1117 | 0.4490 | -99.78 | no pasa la criba |
| 78 | BTCUSDT 5m | `3019a2afcf924d97` | 39181 | 0.4762 | -100 | uno de seis | `67c1d81599fc7b88` | 6481 | 0.5403 | -100 | no pasa la criba |
| 32 | ETHUSDT 5m | `f3b9bf81fd5955f5` | 29824 | 0.4132 | -100 | uno de seis | `56c7db323f3a930d` | 5163 | 0.4634 | -100 | no pasa la criba |
| 3 | ETHUSDT 5m | `491559521c66e482` | 14303 | 0.3514 | -100 | uno de seis | `f66e86232dbb0950` | 2548 | 0.2879 | -100 | no pasa la criba |
| 54 | HYPEUSDT 5m | `bf96b361df0af8b0` | 83 | 0.3284 | -39.37 | uno de seis | `7082b2e73c987b06` | 124 | 0.2198 | -58.22 | no pasa la criba |
| 56 | JUPUSDT 1h | `21205781c5286e31` | 12 | 0.2761 | -7.39 | cero de seis | `e204b9ff9a79060a` | 19 | 1.0437 | 1.02 | INSUFICIENTE MUESTRA |
| 27 | SOLUSDT 15m | `e3f3b411155e2a06` | 11167 | 0.2508 | -100 | uno de seis | `6d2783cc029d7a1a` | 2220 | 0.1621 | -100 | no pasa la criba |
| 31 | JUPUSDT 15m | `89a0d58f87c62b75` | 59 | 0.2266 | -42.59 | uno de seis | `e3b2c06113ac56df` | 95 | 0.1002 | -70.14 | no pasa la criba |
| 35 | HYPEUSDT 1h | `d98d44836749340a` | 6 | 0.2235 | -3.62 | cero de seis | `10d08ac97ca8c4a1` | 13 | 2.1778 | 10.51 | INSUFICIENTE MUESTRA |
| 67 | ETHUSDT 15m | `4818b3682c7c3b8e` | 28247 | 0.1986 | -100 | uno de seis | `c203eb6420611b96` | 5381 | 0.2649 | -100 | no pasa la criba |
| 19 | BTCUSDT 15m | `e8eb6bc3e2f8f5b2` | 57561 | 0.1462 | -100 | uno de seis | `0adaa952927e1451` | 9478 | 0.2123 | -100 | no pasa la criba |
| 41 | HYPEUSDT 5m | `05c33e26183aa219` | 53 | 0.0453 | -48.86 | uno de seis | `e8098a522c1e1aed` | 63 | 2.0252 | 47.56 | no pasa la criba |
| 46 | SOLUSDT 15m | `33664d78f146f298` | 36 | 0 | -29.50 | uno de seis | `3071ab158b8802ed` | 10 | 0 | -9.40 | no pasa la criba |
| 49 | SUIUSDT 1h | `3951d3831c8ddefc` | 14 | 0 | -13.70 | cero de seis | `977c7910aecfca88` | 6 | 2.6441 | 7.61 | INSUFICIENTE MUESTRA |
| 58 | BTCUSDT 1h | `565bfb292760aa5f` | 3 | 0 | -3.37 | cero de seis | `bf377b8d6c6db9a0` | 0 | 0 | 0 | INSUFICIENTE MUESTRA |
| 77 | JUPUSDT 15m | `d02b635a715ff727` | 0 | 0 | 0 | cero de seis | `ed3b9066693da475` | 0 | 0 | 0 | INSUFICIENTE MUESTRA |

## Gates, prompt por prompt (los que pasan la criba)

### #85 HYPEUSDT 1h

- DEV: artefacto `results/runs/5d6948a96488bd1e` (run_id `5d6948a96488bd1e`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 2.4884 |
| at least thirty closed trades | PASS | n = 127 |
| net return above zero | PASS | net = 26.36 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 81.71 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0721 |

- OOS: artefacto `results/runs/6695aa5b5a751e97` (run_id `6695aa5b5a751e97`)

| gate (OOS) | resultado | medido |
|---|---|---|
| at least one hundred closed trades | PASS | n = 383 |
| profit factor ex-cost above one point two | PASS | PF = 2.9236 |
| net return above zero | PASS | net = 401.15 % |
| conc: without the five best the result is still positive | PASS | net without them = 62.11 % |
| two of the three thirds green | PASS | 3 of three green |
| the bootstrap interval above zero | PASS | CI low = 0.1074 |

- buy & hold del mismo tramo: 71.19 %; exceso del libro: 329.95 pp
- fees pagados 18340.35 USDT, funding -14846.34 USDT, resoluo del invariante -0.0000000001
- **nocional implicito 52.4x el equity** (máximo 4726.8x): el libro no es certificable, y sus cifras miden la apalancamiento, no la señal

### #44 BTCUSDT 1h

- DEV: artefacto `results/runs/f4cc570d6b8b8199` (run_id `f4cc570d6b8b8199`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 2.2929 |
| at least thirty closed trades | PASS | n = 136 |
| net return above zero | PASS | net = 253.78 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 81.86 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.4387 |

- OOS: artefacto `results/runs/2e739e5705368a7f` (run_id `2e739e5705368a7f`)

| gate (OOS) | resultado | medido |
|---|---|---|
| at least one hundred closed trades | FAIL | n = 22 |
| profit factor ex-cost above one point two | PASS | PF = 1.3816 |
| net return above zero | PASS | net = 5.94 % |
| conc: without the five best the result is still positive | FAIL | net without them = -17.12 % |
| two of the three thirds green | FAIL | 1 of three green |
| the bootstrap interval above zero | FAIL | CI low = -1 |

- buy & hold del mismo tramo: -29.09 %; exceso del libro: 35.03 pp
- fees pagados 138.61 USDT, funding 75.40 USDT, resoluo del invariante 0

### #28 BTCUSDT 1h

- DEV: artefacto `results/runs/bb1b90c42f6bfd4b` (run_id `bb1b90c42f6bfd4b`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 1.3360 |
| at least thirty closed trades | PASS | n = 366 |
| net return above zero | PASS | net = 73.28 % |
| two of the three thirds green | PASS | 2 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 80.09 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0076 |

- OOS: artefacto `results/runs/8cbdb2c8ddd2c132` (run_id `8cbdb2c8ddd2c132`)

| gate (OOS) | resultado | medido |
|---|---|---|
| at least one hundred closed trades | FAIL | n = 63 |
| profit factor ex-cost above one point two | FAIL | PF = 0.7882 |
| net return above zero | FAIL | net = -8.22 % |
| conc: without the five best the result is still positive | FAIL | net without them = -33.27 % |
| two of the three thirds green | FAIL | 1 of three green |
| the bootstrap interval above zero | FAIL | CI low = -0.5857 |

- buy & hold del mismo tramo: -29.09 %; exceso del libro: 20.87 pp
- fees pagados 373.56 USDT, funding 54.88 USDT, resoluo del invariante 0

### #26 ETHUSDT 1h

- DEV: artefacto `results/runs/c702db037672f1fe` (run_id `c702db037672f1fe`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 1.2622 |
| at least thirty closed trades | PASS | n = 942 |
| net return above zero | PASS | net = 319.09 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 75 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0471 |

- OOS: artefacto `results/runs/7d70052d9015b588` (run_id `7d70052d9015b588`)

| gate (OOS) | resultado | medido |
|---|---|---|
| at least one hundred closed trades | PASS | n = 183 |
| profit factor ex-cost above one point two | FAIL | PF = 1.0348 |
| net return above zero | PASS | net = 3.17 % |
| conc: without the five best the result is still positive | FAIL | net without them = -62.20 % |
| two of the three thirds green | PASS | 2 of three green |
| the bootstrap interval above zero | FAIL | CI low = -0.2782 |

- buy & hold del mismo tramo: -40.67 %; exceso del libro: 43.84 pp
- fees pagados 975.25 USDT, funding 72.86 USDT, resoluo del invariante 0

## La criba (DEV) y el veredicto (OOS): pares y cestas

Estas filas son **NO CERTIFICABLES**: el nocional implicito de su dimensionamiento no es sostenible (el tope del propio pack es 20x el equity por posicion). Se publican sus cifras measuradas, pero como **evidencia del defecto del dimensionamiento**, no como un resultado de estrategia: con esa palanca el funding, que el pack ignora, pesa mas que la senal.

| # | prompt | legs | run_id DEV | n DEV | PF DEV | run_id OOS | n OOS | PF OOS | nocional implicito (x equity) | veredicto |
|---|---|---|---|---:|---:|---|---:|---:|---:|---|
| 85 | HYPEUSDT 1h | `5d6948a96488bd1e` | 127 | 2.4884 | `6695aa5b5a751e97` | 383 | 2.9236 | 52.4 | NO CERTIFICABLE (nocional) |
| 88 | BTCUSDT 1h | `7389494f488aeead` | 2433 | 1.1656 | `b99001076321ff43` | 368 | 1.5177 | - | no supera el veredicto |
| 90 | BASKET6 1h | `d3ee28ea993e4d59` | 124 | 1.1175 | `dbaf574930fde436` | 53 | 1.2766 | - | no supera el veredicto |
| 83 | BASKET6 1h | `cc2db65ccae05a34` | 125 | 1.0649 | `580a821fd2140be2` | 53 | 1.3800 | - | no supera el veredicto |
| 84 | BASKET6 1h | `65d29281737d31d1` | 2134 | 0.8698 | `ea669c227c5d128c` | 463 | 0.7721 | - | no supera el veredicto |
| 86 | SUIUSDT 1h | `6a68261f066ccefb` | 145 | 0.7546 | `e272ef10e2185382` | 106 | 0.0536 | 0 | no supera el veredicto |
| 87 | BASKET6 1h | `3d18c869a631a825` | 126 | 0.5675 | `c86bcede06c28272` | 53 | 0.4713 | - | no supera el veredicto |
| 82 | BTCUSDT 1h | `2a0dc863f13a0af6` | 517 | 0.3982 | `0c09baffa3b0c0e3` | 103 | 0.1942 | 236795.5 | NO CERTIFICABLE (nocional) |
| 81 | SOLUSDT 1h | `0c0f2732c2926336` | 215 | 0.2683 | `b549c9d4ff675fec` | 44 | 0.8290 | 2940.9 | NO CERTIFICABLE (nocional) |
| 89 | ETHUSDT 15m | `d0475bd09247a3bd` | 598 | 0.0855 | `9d04ac411330d369` | 111 | 6.7333 | 1350557.5 | NO CERTIFICABLE (nocional) |

## El control de multiplicidad

Con cien prompts cribados, la metrica OOS del ganador esta sesgada al alza: hay que distinguirse del ruido de la propia criba, no de cero. La distribucion completa de los PF de OOS de los prompts medibles se publica aqui, y un superviviente tiene que superar el percentil 95 de esa distribucion.

| prompt | PF OOS |
|---|---:|
| 89 | 6.7333 |
| 85 | 2.9236 |
| 73 | 2.0567 |
| 41 | 2.0252 |
| 88 | 1.5177 |
| 44 | 1.3816 |
| 83 | 1.3800 |
| 60 | 1.3490 |
| 90 | 1.2766 |
| 52 | 1.0705 |
| 71 | 1.0598 |
| 26 | 1.0348 |
| 45 | 1.0137 |
| 34 | 0.9492 |
| 55 | 0.9361 |
| 37 | 0.9064 |
| 30 | 0.8996 |
| 11 | 0.8983 |
| 1 | 0.8822 |
| 24 | 0.8818 |
| 16 | 0.8328 |
| 81 | 0.8290 |
| 10 | 0.8207 |
| 6 | 0.8168 |
| 28 | 0.7882 |
| 68 | 0.7832 |
| 4 | 0.7735 |
| 84 | 0.7721 |
| 69 | 0.7569 |
| 5 | 0.7271 |
| 14 | 0.7247 |
| 15 | 0.7207 |
| 12 | 0.6802 |
| 48 | 0.6636 |
| 74 | 0.6550 |
| 8 | 0.6487 |
| 40 | 0.6457 |
| 39 | 0.6361 |
| 72 | 0.6265 |
| 2 | 0.6174 |
| 7 | 0.6115 |
| 17 | 0.6112 |
| 47 | 0.6031 |
| 36 | 0.5995 |
| 20 | 0.5990 |
| 9 | 0.5960 |
| 18 | 0.5954 |
| 70 | 0.5904 |
| 25 | 0.5856 |
| 33 | 0.5479 |
| 53 | 0.5416 |
| 78 | 0.5403 |
| 13 | 0.5230 |
| 42 | 0.4810 |
| 87 | 0.4713 |
| 66 | 0.4690 |
| 50 | 0.4684 |
| 51 | 0.4673 |
| 32 | 0.4634 |
| 80 | 0.4574 |
| 62 | 0.4490 |
| 79 | 0.4130 |
| 65 | 0.4012 |
| 61 | 0.4005 |
| 3 | 0.2879 |
| 63 | 0.2782 |
| 43 | 0.2704 |
| 67 | 0.2649 |
| 38 | 0.2611 |
| 54 | 0.2198 |
| 19 | 0.2123 |
| 82 | 0.1942 |
| 27 | 0.1621 |
| 23 | 0.1294 |
| 31 | 0.1002 |
| 86 | 0.0536 |
| 64 | 0 |
| 46 | 0 |

El percentil 95 de esa distribucion es **2.0252**. Ningun prompt lo supera: el mejor PF de OOS de la criba se queda en 6.7333.

## La familia de pares y cestas: el nocional manda

Los prompts de par (los seis de spread) no son un libro que se pueda sostener: el dimensionamiento del pack implica un **nocional bruto de decenas de miles de veces el equity**. Eso convierte el funding (que el pack no cobra) en el motor principal del resultado: con esa palanca, unos puntos de funding por settlement pesan mas que el spread. Por eso la puerta de certificabilidad es el nocional, no el profit factor.

| prompt | legs | nocional implicito (x equity) | coste sobre el nocional real por trade (USDT) | funding neto del tramo (USDT) |
|---|---|---:|---:|---:|
| 81 | SOLUSDT 1h | 2940.9 | 49513 | -18726 |
| 82 | BTCUSDT 1h | 236795.5 | 8472759 | 1167073912888322816 |
| 85 | HYPEUSDT 1h | 52.4 | 1274 | -14846 |
| 86 | SUIUSDT 1h | 0 | 1 | 0 |
| 88 | BTCUSDT 1h | - | - | 1682 |
| 89 | ETHUSDT 15m | 1350557.5 | 13059676 | 2535770 |
| 83 | BASKET6 1h | - | - | 21 |
| 84 | BASKET6 1h | - | - | 8 |
| 87 | BASKET6 1h | - | - | 85 |
| 90 | BASKET6 1h | - | - | 0 |

## Los prompts que NO se han medido, y por que

| prompt | simbolo | tf | motivo |
|---|---|---|---|
| 18 | JUPUSDT | 5m | sin klines de ese simbolo y timeframe en el repo: NO DATA, y no se estima nada |
| 43 | JUPUSDT | 5m | sin klines de ese simbolo y timeframe en el repo: NO DATA, y no se estima nada |
| 62 | JUPUSDT | 5m | sin klines de ese simbolo y timeframe en el repo: NO DATA, y no se estima nada |

La familia de prompts de funding del pack (los de funding) es un tercer tipo de libro: su ejecucion necesita el own funding alineado con las klines y una logica de senal distinta. **No se han medido** y no se afirma nada sobre ellos.

## Limites declarados

- Esta pantalla cubre la familia de un solo simbolo y la de par y cesta. Los prompts de funding del pack son un tercer tipo de libro y NO se han medido aqui: no se afirma nada sobre ellos.
- El tramo OOS es comun (desde 2025-11-01) para que las cien estrategias se comparen sobre el mismo regimen, pero cada prompt tiene su propio tramo DEV: los symbols con menos historia (HYPE) tienen un DEV mucho mas corto que BTC.
- Sin modelo de margen ni de liquidacion; el tope de apalancamiento por posicion (20x) es el del pack y, con el tamaño por riesgo del 1 %, nunca aprieta.
- Medicion sobre las klines del repo. No se enviaron ordenes.

## Reproduccion

```
python code/_prompts100_parity.py
python code/_prompts100_audit.py
python code/_p100_screen_run.py
python code/vrun.py verify <run_id>
```

