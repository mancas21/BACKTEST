# Re-screen de los cien prompts del pack con el harness del repo

- generated: `2026-11-22`
- spec congelado antes de la primera corrida: `results/prompts100_rescreen_pre_registration.md`
- codigo del pack copiado verbatim a `code/prompts100/` con manifiesto sha256; motor del repo: `code/p100_screen_engine.py`; adapter `p100screen`
- paridad: `code/_prompts100_parity.py` (trades y metricas identicos al motor del pack); respuestas conocidas: `code/_prompts100_audit.py` (ambas direcciones)
- costes: **el coste resuelto por simbolo** (maximo entre los 11 bps RT por defecto y el RT MEDIDO del cost model `results/cost_model_2026-10-25.json`: fee 5 bps, slip rt/2-5; los libros multi-pierna cobran el maximo de sus piernas) y **funding cobrado en los settlements reales ANTES de los stops intrabar** (fix N11 2026-11-21); el invariante contable se aserta dentro de cada artefacto; el coste resuelto viaja MEDIDO en cada artefacto (`cost_bp_roundtrip`, `cost_source`)

## Veredicto

De los ochenta y nueve prompts medidos, **cuatro** limpian la criba sobre DEV y **cero** superan el veredicto completo sobre OOS (uno de los supervisivientes es pares y no es certificables: su nocional implicito no es sostenible). La razon principal no es el modelo: es el coste. El pack original corria a 2.2 bps round trip (su constante es 0.000055, o sea 0.55 bps por lado, diez veces menos de lo que documenta) y sin funding; el repo cobra 11 bps y el funding real. Ese salto es lo que separa las dos cribas.


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
| 57 | ETHUSDT 15m | `122ab52094ab2798` | 11 | 275.9425 | 1653.51 | tres de seis | `a4253bfc4815f304` | 73 | 0 | -65.29 | INSUFICIENTE MUESTRA |
| 59 | SOLUSDT 1h | `a48b68dcb53e55dd` | 9 | 70.7753 | 441.53 | tres de seis | `9a549a354e01e216` | 30 | 0.3062 | -18.75 | INSUFICIENTE MUESTRA |
| 75 | HYPEUSDT 1h | `a0bdd4f7df3b588c` | 2 | 7.4782 | 5.31 | tres de seis | `2b910c56812485ec` | 9 | 7.0177 | 45.36 | INSUFICIENTE MUESTRA |
| 63 | BTCUSDT 15m | `40f113d0ac541cd4` | 32 | 6.7655 | 102.21 | cuatro de seis | `3c73af4ae2b3c3e8` | 32 | 0.2782 | -25.06 | no pasa la criba |
| 23 | SUIUSDT 15m | `cdf4e9f92a88d7a9` | 69 | 6.3560 | 247.69 | cuatro de seis | `bfdce3d2b84773f3` | 68 | 0.1294 | -46.74 | no pasa la criba |
| 44 | BTCUSDT 1h | `fb21e28ee052a60d` | 136 | 2.2929 | 253.78 | seis de seis | `14b180ea4ff3c5d6` | 22 | 1.3816 | 5.94 | KILLED (veredicto OOS) |
| 64 | ETHUSDT 1h | `89e16b84484306d4` | 42 | 1.8551 | 28.87 | cuatro de seis | `f45df1982a529850` | 15 | 0 | -15.78 | no pasa la criba |
| 29 | HYPEUSDT 15m | `4e8fd491af180f52` | 7 | 1.5191 | 0.73 | tres de seis | `fc9d430e717879c5` | 36 | 2.8990 | 53.91 | INSUFICIENTE MUESTRA |
| 73 | ETHUSDT 1h | `a33800aa4dae0f35` | 106 | 1.4695 | 36.15 | cuatro de seis | `3bfcf46085ed955e` | 19 | 2.0567 | 8.60 | no pasa la criba |
| 22 | HYPEUSDT 1h | `d3a2405f5205ff5c` | 28 | 1.3719 | 3.41 | tres de seis | `3ca1233744fc4f0c` | 95 | 0.8959 | -4.51 | INSUFICIENTE MUESTRA |
| 28 | BTCUSDT 1h | `5ff1cd1d65891dfd` | 366 | 1.3360 | 73.28 | seis de seis | `920d345f5ccfc610` | 63 | 0.7882 | -8.22 | KILLED (veredicto OOS) |
| 68 | SOLUSDT 1h | `92a8c3fc84a2efaa` | 263 | 1.3253 | 55.03 | cinco de seis | `8910b0ecd2bcd4b5` | 52 | 0.7832 | -7 | no pasa la criba |
| 45 | ETHUSDT 1h | `46a49c2b9d936fdb` | 622 | 1.2748 | 264.49 | cinco de seis | `134dbd1a9c250ef6` | 124 | 1.0137 | 0.77 | no pasa la criba |
| 26 | ETHUSDT 1h | `1ac7e39f8d9adde6` | 942 | 1.2622 | 319.09 | seis de seis | `523271a06c54f3ac` | 183 | 1.0348 | 3.17 | KILLED (veredicto OOS) |
| 72 | BTCUSDT 1h | `5cb9aff4d869d615` | 317 | 1.1512 | 32.78 | cuatro de seis | `8fdec47744ca841f` | 53 | 0.6265 | -13.18 | no pasa la criba |
| 52 | BTCUSDT 15m | `3535d48e6aa464e6` | 877 | 1.1320 | 393.33 | cuatro de seis | `ac30f4f0ab24afb1` | 179 | 1.0705 | 13.86 | no pasa la criba |
| 60 | HYPEUSDT 1h | `cf5cbc2341e8f2b1` | 50 | 1.0918 | 1.48 | tres de seis | `e3771ef33c43f477` | 141 | 1.3490 | 23.10 | no pasa la criba |
| 34 | SOLUSDT 1h | `75a0f540815c83a9` | 1561 | 1.0849 | 118.68 | tres de seis | `63b3bf3bb6ef8630` | 335 | 0.9492 | -10.27 | no pasa la criba |
| 21 | SOLUSDT 1h | `d11e79a2cdd2c7e2` | 27 | 0.9948 | -0.34 | cero de seis | `82f124080d96aaa7` | 8 | 1.5191 | 2.69 | INSUFICIENTE MUESTRA |
| 4 | HYPEUSDT 1h | `81452f6f11963744` | 127 | 0.9900 | -1.12 | dos de seis | `c7e5639bab081df1` | 386 | 0.7735 | -34.57 | no pasa la criba |
| 69 | HYPEUSDT 15m | `02a334d34caf0421` | 61 | 0.9834 | -0.59 | dos de seis | `b27bc45b39fdba7a` | 151 | 0.7569 | -22.75 | no pasa la criba |
| 47 | BTCUSDT 5m | `42ab3ea9d7889174` | 7900 | 0.9657 | -100 | uno de seis | `4fef58ba9498015d` | 1627 | 0.6031 | -99.98 | no pasa la criba |
| 53 | SOLUSDT 5m | `8271cf66754a8be0` | 3322 | 0.9501 | -99.69 | uno de seis | `a53e5fd8df72a13d` | 711 | 0.5416 | -96.30 | no pasa la criba |
| 7 | BTCUSDT 1h | `4f9fbb099a4f23cf` | 1083 | 0.8985 | -44.65 | uno de seis | `bfcd3b12a2403f3c` | 138 | 0.6115 | -20.54 | no pasa la criba |
| 10 | HYPEUSDT 15m | `07360ec7efda6377` | 213 | 0.8981 | -6.49 | uno de seis | `8fb65628cb32538d` | 699 | 0.8207 | -30.81 | no pasa la criba |
| 11 | SUIUSDT 1h | `618ee62d1acacb1f` | 171 | 0.8957 | -6.23 | uno de seis | `ac308664a6ce72ae` | 79 | 0.8983 | -2.77 | no pasa la criba |
| 16 | HYPEUSDT 5m | `1aec8d2f9648b8b5` | 759 | 0.8915 | -57.43 | uno de seis | `c85f6e2235b25802` | 1991 | 0.8328 | -98.04 | no pasa la criba |
| 76 | SUIUSDT 5m | `5d3d133372166af2` | 23 | 0.8911 | -1.43 | cero de seis | `8a7191589e4e6a62` | 18 | 0.8933 | -1.83 | INSUFICIENTE MUESTRA |
| 14 | ETHUSDT 1h | `e00840c1205c0bec` | 742 | 0.8831 | -41.69 | uno de seis | `f0616e29a9cec7f4` | 106 | 0.7247 | -17.63 | no pasa la criba |
| 40 | SOLUSDT 5m | `2c8b66f41bd38f1f` | 26449 | 0.8794 | -100 | uno de seis | `aa8ae6e0dd6d7c60` | 5739 | 0.6457 | -100 | no pasa la criba |
| 33 | BTCUSDT 15m | `9ab44c2f6f15b04e` | 7246 | 0.8318 | -100 | uno de seis | `4ea8cdf12b687bf0` | 1211 | 0.5479 | -96.36 | no pasa la criba |
| 39 | ETHUSDT 15m | `df9975c59c662bb4` | 5735 | 0.8315 | -99.99 | uno de seis | `7c1395dad24f3fd1` | 1019 | 0.6361 | -91.49 | no pasa la criba |
| 1 | SOLUSDT 1h | `9ef710c61857b23d` | 514 | 0.8165 | -55.42 | uno de seis | `3cc228209a901bfb` | 123 | 0.8822 | -9.76 | no pasa la criba |
| 30 | SUIUSDT 1h | `c064b32f250729c2` | 339 | 0.8142 | -26.56 | uno de seis | `2b2c0a5873cd4795` | 108 | 0.8996 | -5.87 | no pasa la criba |
| 37 | JUPUSDT 1h | `86bb4d7245accade` | 1374 | 0.8098 | -68.62 | uno de seis | `ef2c3da68f47ee5f` | 805 | 0.9064 | -27.07 | no pasa la criba |
| 74 | SOLUSDT 15m | `44aa590c1f6f3534` | 1836 | 0.7985 | -84.14 | uno de seis | `d96ba952a4682d88` | 373 | 0.6550 | -49.98 | no pasa la criba |
| 15 | SOLUSDT 15m | `57d2226e91b6b75d` | 5566 | 0.7955 | -99.99 | uno de seis | `939072b175a4e69b` | 1143 | 0.7207 | -91.74 | no pasa la criba |
| 80 | SOLUSDT 5m | `ac6166b650ef0267` | 1829 | 0.7940 | -99.19 | uno de seis | `40839e8fb189420e` | 361 | 0.4574 | -77.85 | no pasa la criba |
| 55 | SUIUSDT 15m | `2ee3d21708b73e38` | 1339 | 0.7581 | -84.54 | uno de seis | `b56aedda8198c0db` | 503 | 0.9361 | -23.26 | no pasa la criba |
| 5 | SUIUSDT 15m | `51d4afd36943fa5a` | 3194 | 0.7446 | -99.45 | uno de seis | `4bf8b432025a19e6` | 1297 | 0.7271 | -91.55 | no pasa la criba |
| 6 | JUPUSDT 1h | `757a80603f4b0c86` | 421 | 0.7419 | -35.28 | uno de seis | `373c436ae3ae4f99` | 249 | 0.8168 | -14.81 | no pasa la criba |
| 48 | HYPEUSDT 15m | `b1a0d4255a2200b9` | 1661 | 0.7356 | -86.74 | uno de seis | `89a271983febb70c` | 5152 | 0.6636 | -99.99 | no pasa la criba |
| 8 | ETHUSDT 15m | `42a81896d05459a6` | 5474 | 0.7269 | -100 | uno de seis | `d626f511c0de527a` | 1034 | 0.6487 | -91.76 | no pasa la criba |
| 24 | JUPUSDT 1h | `521dc44037629cc6` | 349 | 0.7243 | -44.19 | uno de seis | `5624786013632f4c` | 174 | 0.8818 | -10 | no pasa la criba |
| 9 | SOLUSDT 5m | `5869ba5b9148d292` | 9420 | 0.7149 | -100 | uno de seis | `561f30aa6474f8f3` | 2036 | 0.5960 | -99.98 | no pasa la criba |
| 36 | SUIUSDT 5m | `77fcd240f332eb8e` | 2295 | 0.6884 | -97.56 | uno de seis | `3a952d5c85e6edca` | 991 | 0.5995 | -98.57 | no pasa la criba |
| 20 | ETHUSDT 5m | `d483cdd526d87ddf` | 8856 | 0.6556 | -100 | uno de seis | `8e92f0dd46b332f2` | 1677 | 0.5990 | -99.87 | no pasa la criba |
| 71 | JUPUSDT 1h | `3987a9728ed10c2c` | 62 | 0.6538 | -16.36 | uno de seis | `6c530d1bbca5d0a0` | 43 | 1.0598 | 2.01 | no pasa la criba |
| 43 | JUPUSDT 5m | `90b9ce215a126152` | 4708 | 0.6348 | -100 | uno de seis | `399d0f16683d5274` | 3005 | 0.2704 | -100 | no pasa la criba |
| 50 | JUPUSDT 15m | `6ee5065cb893f5ea` | 12452 | 0.6347 | -100 | uno de seis | `c9311d8dd7d4c485` | 7260 | 0.4684 | -100 | no pasa la criba |
| 25 | BTCUSDT 1h | `94adb0c6c6fd583a` | 1213 | 0.6308 | -84.50 | uno de seis | `ecac97f17347958f` | 208 | 0.5856 | -31.11 | no pasa la criba |
| 65 | SOLUSDT 15m | `06e76f8d9a1c9a2b` | 1729 | 0.6295 | -88.09 | uno de seis | `99e1801ffc9bbfeb` | 291 | 0.4012 | -44.10 | no pasa la criba |
| 18 | JUPUSDT 5m | `b35a9fafae142a41` | 3029 | 0.6153 | -100 | uno de seis | `ceefff19696975b9` | 2143 | 0.5954 | -99.98 | no pasa la criba |
| 17 | SUIUSDT 5m | `222731187f80d2a0` | 1603 | 0.6084 | -98.87 | uno de seis | `e0a4ec926a73a1d2` | 561 | 0.6112 | -88.06 | no pasa la criba |
| 70 | SUIUSDT 15m | `18a39cef1ee36287` | 1176 | 0.6081 | -93.61 | uno de seis | `2a8b3f0c62224300` | 536 | 0.5904 | -75.13 | no pasa la criba |
| 79 | ETHUSDT 5m | `826afd344e566cdb` | 13845 | 0.5842 | -100 | uno de seis | `dca37a942efb0e3f` | 2355 | 0.4130 | -100 | no pasa la criba |
| 51 | ETHUSDT 5m | `d62bb79a6dcd03fb` | 11986 | 0.5634 | -100 | uno de seis | `bc87de7b4c9c8cf3` | 2022 | 0.4673 | -99.99 | no pasa la criba |
| 12 | JUPUSDT 15m | `758edbd80068342b` | 99 | 0.5467 | -27.27 | uno de seis | `ef692f09e195bee8` | 173 | 0.6802 | -29.86 | no pasa la criba |
| 42 | SUIUSDT 15m | `035c58c94aea267c` | 7526 | 0.5423 | -99.96 | uno de seis | `91b2a31d0556b537` | 3335 | 0.4810 | -99.65 | no pasa la criba |
| 66 | BTCUSDT 15m | `fb9cc9422c1e9db0` | 3736 | 0.5317 | -100 | uno de seis | `eae7e0b3126a7340` | 600 | 0.4690 | -93.35 | no pasa la criba |
| 2 | BTCUSDT 15m | `4741d676c48139c6` | 4393 | 0.5223 | -100 | uno de seis | `9a40ec2494739476` | 814 | 0.6174 | -91.89 | no pasa la criba |
| 13 | BTCUSDT 5m | `fdcbd403885f3c7f` | 3220 | 0.5217 | -100 | uno de seis | `a91497cd1a9619ce` | 664 | 0.5230 | -97.58 | no pasa la criba |
| 38 | BTCUSDT 5m | `dc9974b33ed8b5a4` | 12049 | 0.5140 | -100 | uno de seis | `1a69191bebd1ec8d` | 1951 | 0.2611 | -100 | no pasa la criba |
| 61 | SUIUSDT 5m | `3ea95d576a60c978` | 870 | 0.4799 | -98.83 | uno de seis | `d77ea050b996ff85` | 354 | 0.4005 | -89.37 | no pasa la criba |
| 62 | JUPUSDT 5m | `dd9c063cb1941e2b` | 1425 | 0.4788 | -99.86 | uno de seis | `f0b5fcd711bc50c8` | 1117 | 0.4490 | -99.78 | no pasa la criba |
| 78 | BTCUSDT 5m | `a13bd78a892a7c71` | 39181 | 0.4762 | -100 | uno de seis | `c9cd48a34d5ac76a` | 6481 | 0.5403 | -100 | no pasa la criba |
| 32 | ETHUSDT 5m | `12ea50f0d4f5a731` | 29824 | 0.4132 | -100 | uno de seis | `e01474bdd0a1be6c` | 5163 | 0.4634 | -100 | no pasa la criba |
| 3 | ETHUSDT 5m | `86bbb2a81e8b3922` | 14303 | 0.3514 | -100 | uno de seis | `1a6c9b56b97e42fb` | 2548 | 0.2879 | -100 | no pasa la criba |
| 54 | HYPEUSDT 5m | `8527f419b9093c12` | 83 | 0.3284 | -39.37 | uno de seis | `eb915353a882e0b1` | 124 | 0.2198 | -58.22 | no pasa la criba |
| 56 | JUPUSDT 1h | `1b46607f9a49dd5a` | 12 | 0.2761 | -7.39 | cero de seis | `dbf07043fcf53bb7` | 19 | 1.0437 | 1.02 | INSUFICIENTE MUESTRA |
| 27 | SOLUSDT 15m | `fa9b28eefbb877b2` | 11167 | 0.2508 | -100 | uno de seis | `867e639a1322ed51` | 2220 | 0.1621 | -100 | no pasa la criba |
| 31 | JUPUSDT 15m | `4707dfb2b01b960f` | 59 | 0.2266 | -42.59 | uno de seis | `9b50a59f3a8f646c` | 95 | 0.1002 | -70.14 | no pasa la criba |
| 35 | HYPEUSDT 1h | `3caa00a914d2ba56` | 6 | 0.2235 | -3.62 | cero de seis | `950fb36afb86612c` | 13 | 2.1778 | 10.51 | INSUFICIENTE MUESTRA |
| 67 | ETHUSDT 15m | `28395b2cf255c689` | 28247 | 0.1986 | -100 | uno de seis | `4b2b56b79eb912bf` | 5381 | 0.2649 | -100 | no pasa la criba |
| 19 | BTCUSDT 15m | `323a5339918c8540` | 57561 | 0.1462 | -100 | uno de seis | `10ef0d4c954012ff` | 9478 | 0.2123 | -100 | no pasa la criba |
| 41 | HYPEUSDT 5m | `8effc9766eeb9eaf` | 53 | 0.0453 | -48.86 | uno de seis | `f345468589eeeddf` | 63 | 2.0252 | 47.56 | no pasa la criba |
| 46 | SOLUSDT 15m | `328908baf7776d9a` | 36 | 0 | -29.50 | uno de seis | `cb10462d025e7f33` | 10 | 0 | -9.40 | no pasa la criba |
| 49 | SUIUSDT 1h | `d675459012989a35` | 14 | 0 | -13.70 | cero de seis | `9f71e23623444089` | 6 | 2.6441 | 7.61 | INSUFICIENTE MUESTRA |
| 58 | BTCUSDT 1h | `9d40a0f933e53a8c` | 3 | 0 | -3.37 | cero de seis | `cfd5b15dcdc84fa6` | 0 | 0 | 0 | INSUFICIENTE MUESTRA |
| 77 | JUPUSDT 15m | `bbfdbc4a77a05fa5` | 0 | 0 | 0 | cero de seis | `cc8ba4b24360d1fe` | 0 | 0 | 0 | INSUFICIENTE MUESTRA |

## Gates, prompt por prompt (los que pasan la criba)

### #85 HYPEUSDT 1h

- DEV: artefacto `results/runs/9fd82c58e51b8201` (run_id `9fd82c58e51b8201`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 2.4884 |
| at least thirty closed trades | PASS | n = 127 |
| net return above zero | PASS | net = 26.36 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 81.71 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0721 |

- OOS: artefacto `results/runs/4a449a7d405fbfce` (run_id `4a449a7d405fbfce`)

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

- DEV: artefacto `results/runs/fb21e28ee052a60d` (run_id `fb21e28ee052a60d`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 2.2929 |
| at least thirty closed trades | PASS | n = 136 |
| net return above zero | PASS | net = 253.78 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 81.86 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.4387 |

- OOS: artefacto `results/runs/14b180ea4ff3c5d6` (run_id `14b180ea4ff3c5d6`)

| gate (OOS) | resultado | medido |
|---|---|---|
| at least one hundred closed trades | FAIL | n = 22 |
| profit factor ex-cost above one point two | PASS | PF = 1.3816 |
| net return above zero | PASS | net = 5.94 % |
| conc: without the five best the result is still positive | FAIL | net without them = -17.12 % |
| two of the three thirds green | FAIL | 1 of three green |
| the bootstrap interval above zero | FAIL | CI low = - |

- buy & hold del mismo tramo: -29.09 %; exceso del libro: 35.03 pp
- fees pagados 138.61 USDT, funding 75.40 USDT, resoluo del invariante 0

### #28 BTCUSDT 1h

- DEV: artefacto `results/runs/5ff1cd1d65891dfd` (run_id `5ff1cd1d65891dfd`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 1.3360 |
| at least thirty closed trades | PASS | n = 366 |
| net return above zero | PASS | net = 73.28 % |
| two of the three thirds green | PASS | 2 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 80.09 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0076 |

- OOS: artefacto `results/runs/920d345f5ccfc610` (run_id `920d345f5ccfc610`)

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

- DEV: artefacto `results/runs/1ac7e39f8d9adde6` (run_id `1ac7e39f8d9adde6`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 1.2622 |
| at least thirty closed trades | PASS | n = 942 |
| net return above zero | PASS | net = 319.09 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 75 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0471 |

- OOS: artefacto `results/runs/523271a06c54f3ac` (run_id `523271a06c54f3ac`)

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
| 85 | HYPEUSDT 1h | `9fd82c58e51b8201` | 127 | 2.4884 | `4a449a7d405fbfce` | 383 | 2.9236 | 52.4 | NO CERTIFICABLE (nocional) |
| 90 | BASKET6 1h | `190fd660905bc971` | 124 | 1.1175 | `2cc13531b82770de` | 53 | 1.2766 | - | no supera el veredicto |
| 83 | BASKET6 1h | `13b22ea26cc6b2a4` | 125 | 1.0649 | `af7b2f27256a274c` | 53 | 1.3800 | - | no supera el veredicto |
| 84 | BASKET6 1h | `d806c60c58cccdb6` | 2134 | 0.8698 | `4d6a6796cf29fa86` | 463 | 0.7721 | - | no supera el veredicto |
| 86 | SUIUSDT 1h | `138634ea347404f9` | 145 | 0.7546 | `9cacc17b59037b7b` | 106 | 0.0536 | 0 | no supera el veredicto |
| 87 | BASKET6 1h | `79357ed0edebbfdc` | 126 | 0.5675 | `33fc545969e480bd` | 53 | 0.4713 | - | no supera el veredicto |
| 82 | BTCUSDT 1h | `075a0832f8e4ba29` | 517 | 0.3982 | `b37cd958d94adba5` | 103 | 0.1942 | 236795.5 | NO CERTIFICABLE (nocional) |
| 81 | SOLUSDT 1h | `34c24f1a3799d8ba` | 215 | 0.2683 | `a5d8ada20f7595ba` | 44 | 0.8290 | 2940.9 | NO CERTIFICABLE (nocional) |
| 89 | ETHUSDT 15m | `e08d9a41af3f4240` | 598 | 0.0855 | `a427e48da9d9cdaa` | 111 | 6.7333 | 1350557.5 | NO CERTIFICABLE (nocional) |

## El control de multiplicidad

Con cien prompts cribados, la metrica OOS del ganador esta sesgada al alza: hay que distinguirse del ruido de la propia criba, no de cero. La distribucion completa de los PF de OOS de los prompts medibles se publica aqui, y un superviviente tiene que superar el percentil 95 de esa distribucion.

| prompt | PF OOS |
|---|---:|
| 89 | 6.7333 |
| 85 | 2.9236 |
| 73 | 2.0567 |
| 41 | 2.0252 |
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
| 81 | SOLUSDT 1h | 2940.9 | 53969 | -18726 |
| 82 | BTCUSDT 1h | 236795.5 | 8472759 | 1167073912888322816 |
| 85 | HYPEUSDT 1h | 52.4 | 1388 | -14846 |
| 86 | SUIUSDT 1h | 0 | 2 | 0 |
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
| 81 | SOLUSDT | 1h | el sobre intrabar de la puesta no puede construirse (pierna sintetica sin klines, ALT-BASKET) y el engine la RECHAZA en lugar de degradarla: no certificable bajo la convencion del repo, no se estima nada |
| 82 | BTCUSDT | 1h | el sobre intrabar de la puesta no puede construirse (pierna sintetica sin klines, ALT-BASKET) y el engine la RECHAZA en lugar de degradarla: no certificable bajo la convencion del repo, no se estima nada |
| 85 | HYPEUSDT | 1h | el sobre intrabar de la puesta no puede construirse (pierna sintetica sin klines, ALT-BASKET) y el engine la RECHAZA en lugar de degradarla: no certificable bajo la convencion del repo, no se estima nada |
| 86 | SUIUSDT | 1h | el sobre intrabar de la puesta no puede construirse (pierna sintetica sin klines, ALT-BASKET) y el engine la RECHAZA en lugar de degradarla: no certificable bajo la convencion del repo, no se estima nada |
| 88 | BASKET6 | 1h | el sobre intrabar de la puesta no puede construirse (pierna sintetica sin klines, ALT-BASKET) y el engine la RECHAZA en lugar de degradarla: no certificable bajo la convencion del repo, no se estima nada |
| 89 | ETHUSDT | 15m | el sobre intrabar de la puesta no puede construirse (pierna sintetica sin klines, ALT-BASKET) y el engine la RECHAZA en lugar de degradarla: no certificable bajo la convencion del repo, no se estima nada |

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

