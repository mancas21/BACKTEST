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
| 57 | ETHUSDT 15m | `09dba2448aa6364a` | 11 | 275.9425 | 1653.51 | tres de seis | `5bc8aa86fb01a043` | 73 | 0 | -65.29 | INSUFICIENTE MUESTRA |
| 59 | SOLUSDT 1h | `4b2997dec4de2e98` | 9 | 70.7753 | 441.53 | tres de seis | `ee535011b54378a3` | 30 | 0.3062 | -18.75 | INSUFICIENTE MUESTRA |
| 75 | HYPEUSDT 1h | `7ae64d5e5d712558` | 2 | 7.4782 | 5.31 | tres de seis | `3673978700359fbe` | 9 | 7.0177 | 45.36 | INSUFICIENTE MUESTRA |
| 63 | BTCUSDT 15m | `a0e8c84b28e06c90` | 32 | 6.7655 | 102.21 | cuatro de seis | `363c3376e632b0f0` | 32 | 0.2782 | -25.06 | no pasa la criba |
| 23 | SUIUSDT 15m | `1c7ac8d6e322c38d` | 69 | 6.3560 | 247.69 | cuatro de seis | `25ad121edf718b6a` | 68 | 0.1294 | -46.74 | no pasa la criba |
| 44 | BTCUSDT 1h | `15ef339d9e9f803e` | 136 | 2.2929 | 253.78 | seis de seis | `983185447057c499` | 22 | 1.3816 | 5.94 | KILLED (veredicto OOS) |
| 64 | ETHUSDT 1h | `f0493749c111c075` | 42 | 1.8551 | 28.87 | cuatro de seis | `fcdabb90dc3f911d` | 15 | 0 | -15.78 | no pasa la criba |
| 29 | HYPEUSDT 15m | `61b0dfefd990f613` | 7 | 1.5191 | 0.73 | tres de seis | `700f9617c8162f11` | 36 | 2.8990 | 53.91 | INSUFICIENTE MUESTRA |
| 73 | ETHUSDT 1h | `52e030247c720ace` | 106 | 1.4695 | 36.15 | cuatro de seis | `6c3849301aef820a` | 19 | 2.0567 | 8.60 | no pasa la criba |
| 22 | HYPEUSDT 1h | `b4e258a9abe4bd8c` | 28 | 1.3719 | 3.41 | tres de seis | `5b5f32a282129ec1` | 95 | 0.8959 | -4.51 | INSUFICIENTE MUESTRA |
| 28 | BTCUSDT 1h | `ba1affc9cac66742` | 366 | 1.3360 | 73.28 | seis de seis | `62756db11ecaa1c4` | 63 | 0.7882 | -8.22 | KILLED (veredicto OOS) |
| 68 | SOLUSDT 1h | `566f7704702e9e22` | 263 | 1.3253 | 55.03 | cinco de seis | `71c8065dbfb6a3b4` | 52 | 0.7832 | -7 | no pasa la criba |
| 45 | ETHUSDT 1h | `5f0226e37a53895b` | 622 | 1.2748 | 264.49 | cinco de seis | `3ccffb3f905bb7ca` | 124 | 1.0137 | 0.77 | no pasa la criba |
| 26 | ETHUSDT 1h | `e70997443c6b0aad` | 942 | 1.2622 | 319.09 | seis de seis | `ec1d39c4f5668d89` | 183 | 1.0348 | 3.17 | KILLED (veredicto OOS) |
| 72 | BTCUSDT 1h | `37795d51bc86d487` | 317 | 1.1512 | 32.78 | cuatro de seis | `31e5e93181d8e7d0` | 53 | 0.6265 | -13.18 | no pasa la criba |
| 52 | BTCUSDT 15m | `abf1a9abbb9c4a1f` | 877 | 1.1320 | 393.33 | cuatro de seis | `5c4543b428385e5d` | 179 | 1.0705 | 13.86 | no pasa la criba |
| 60 | HYPEUSDT 1h | `36a4e7b74b1dc085` | 50 | 1.0918 | 1.48 | tres de seis | `b831d2a3b7002fc9` | 141 | 1.3490 | 23.10 | no pasa la criba |
| 34 | SOLUSDT 1h | `12813752a75dcbaf` | 1561 | 1.0849 | 118.68 | tres de seis | `b1d8a6af75ce5aa2` | 335 | 0.9492 | -10.27 | no pasa la criba |
| 21 | SOLUSDT 1h | `6f986c79f799b9a3` | 27 | 0.9948 | -0.34 | cero de seis | `a5d5858e5e8ce097` | 8 | 1.5191 | 2.69 | INSUFICIENTE MUESTRA |
| 4 | HYPEUSDT 1h | `575b85a5301d6639` | 127 | 0.9900 | -1.12 | dos de seis | `6e328eb82f23c667` | 386 | 0.7735 | -34.57 | no pasa la criba |
| 69 | HYPEUSDT 15m | `fc1d5bce9348e063` | 61 | 0.9834 | -0.59 | dos de seis | `ecdabe0aa4f1156a` | 151 | 0.7569 | -22.75 | no pasa la criba |
| 47 | BTCUSDT 5m | `6eb0e0cc00cf0eae` | 7900 | 0.9657 | -100 | uno de seis | `54c6c4bbd1911b71` | 1627 | 0.6031 | -99.98 | no pasa la criba |
| 53 | SOLUSDT 5m | `072ba6d768eb336e` | 3322 | 0.9501 | -99.69 | uno de seis | `9b8e989633e443fd` | 711 | 0.5416 | -96.30 | no pasa la criba |
| 7 | BTCUSDT 1h | `6df7114f7d898a5b` | 1083 | 0.8985 | -44.65 | uno de seis | `eab139ce5ace9dc1` | 138 | 0.6115 | -20.54 | no pasa la criba |
| 10 | HYPEUSDT 15m | `83a7c58fa72ca3c9` | 213 | 0.8981 | -6.49 | uno de seis | `9a0a3058677d9f4e` | 699 | 0.8207 | -30.81 | no pasa la criba |
| 11 | SUIUSDT 1h | `4fa92a8551348db1` | 171 | 0.8957 | -6.23 | uno de seis | `17e864953254a2b8` | 79 | 0.8983 | -2.77 | no pasa la criba |
| 16 | HYPEUSDT 5m | `a5b60ca894df4326` | 759 | 0.8915 | -57.43 | uno de seis | `b21af23441961815` | 1991 | 0.8328 | -98.04 | no pasa la criba |
| 76 | SUIUSDT 5m | `ab96ed1346424043` | 23 | 0.8911 | -1.43 | cero de seis | `97f176794d8e37ea` | 18 | 0.8933 | -1.83 | INSUFICIENTE MUESTRA |
| 14 | ETHUSDT 1h | `fb72e98843a5e555` | 742 | 0.8831 | -41.69 | uno de seis | `4cb9d4f6762e6f84` | 106 | 0.7247 | -17.63 | no pasa la criba |
| 40 | SOLUSDT 5m | `e9c22c8fd0fa1dca` | 26449 | 0.8794 | -100 | uno de seis | `f0d5f3019a94dc39` | 5739 | 0.6457 | -100 | no pasa la criba |
| 33 | BTCUSDT 15m | `bf0f74972cb99700` | 7246 | 0.8318 | -100 | uno de seis | `8f899b4b6b9c047b` | 1211 | 0.5479 | -96.36 | no pasa la criba |
| 39 | ETHUSDT 15m | `f620a232f1d0c50f` | 5735 | 0.8315 | -99.99 | uno de seis | `db5400853d380640` | 1019 | 0.6361 | -91.49 | no pasa la criba |
| 1 | SOLUSDT 1h | `ea63999ed1267af3` | 514 | 0.8165 | -55.42 | uno de seis | `fec5fd4f181d6088` | 123 | 0.8822 | -9.76 | no pasa la criba |
| 30 | SUIUSDT 1h | `46b4da603f7ca813` | 339 | 0.8142 | -26.56 | uno de seis | `d4812366d7ef9f02` | 108 | 0.8996 | -5.87 | no pasa la criba |
| 37 | JUPUSDT 1h | `50ce6b0733e2aacd` | 1374 | 0.8098 | -68.62 | uno de seis | `f5c181994fd36a39` | 805 | 0.9064 | -27.07 | no pasa la criba |
| 74 | SOLUSDT 15m | `709bf3d6de6963f8` | 1836 | 0.7985 | -84.14 | uno de seis | `465171d521bd295b` | 373 | 0.6550 | -49.98 | no pasa la criba |
| 15 | SOLUSDT 15m | `feb89fc2e1c76a1e` | 5566 | 0.7955 | -99.99 | uno de seis | `6278674106505488` | 1143 | 0.7207 | -91.74 | no pasa la criba |
| 80 | SOLUSDT 5m | `8b84cc5685d45fc9` | 1829 | 0.7940 | -99.19 | uno de seis | `64bd611cf40a8d31` | 361 | 0.4574 | -77.85 | no pasa la criba |
| 55 | SUIUSDT 15m | `27b27d57fea0a8dc` | 1339 | 0.7581 | -84.54 | uno de seis | `411224339f1852d3` | 503 | 0.9361 | -23.26 | no pasa la criba |
| 5 | SUIUSDT 15m | `2d3dd4fa6aa9087e` | 3194 | 0.7446 | -99.45 | uno de seis | `fb549f8ea36697bd` | 1297 | 0.7271 | -91.55 | no pasa la criba |
| 6 | JUPUSDT 1h | `7825884de791227c` | 421 | 0.7419 | -35.28 | uno de seis | `5e996f953ab20795` | 249 | 0.8168 | -14.81 | no pasa la criba |
| 48 | HYPEUSDT 15m | `d2fbf9a0bd6044a4` | 1661 | 0.7356 | -86.74 | uno de seis | `d9b3f21a987e7e9b` | 5152 | 0.6636 | -99.99 | no pasa la criba |
| 8 | ETHUSDT 15m | `ef0144f2d97a6a04` | 5474 | 0.7269 | -100 | uno de seis | `935abd3e7e9254d0` | 1034 | 0.6487 | -91.76 | no pasa la criba |
| 24 | JUPUSDT 1h | `33fe4bc3a4061ff8` | 349 | 0.7243 | -44.19 | uno de seis | `4d8e0599a310e93d` | 174 | 0.8818 | -10 | no pasa la criba |
| 9 | SOLUSDT 5m | `d10808af5439d584` | 9420 | 0.7149 | -100 | uno de seis | `aa632c55d3a2a495` | 2036 | 0.5960 | -99.98 | no pasa la criba |
| 36 | SUIUSDT 5m | `19a0bb498cf34317` | 2295 | 0.6884 | -97.56 | uno de seis | `dbcfe94f21fd687d` | 991 | 0.5995 | -98.57 | no pasa la criba |
| 20 | ETHUSDT 5m | `4d526dfb0726888f` | 8856 | 0.6556 | -100 | uno de seis | `5e5d274a6022ea7e` | 1677 | 0.5990 | -99.87 | no pasa la criba |
| 71 | JUPUSDT 1h | `12eb4fa44ec0279c` | 62 | 0.6538 | -16.36 | uno de seis | `71cc0d8be82dd799` | 43 | 1.0598 | 2.01 | no pasa la criba |
| 43 | JUPUSDT 5m | `d8976b3462186fc1` | 4708 | 0.6348 | -100 | uno de seis | `fe0a897389c4148d` | 3005 | 0.2704 | -100 | no pasa la criba |
| 50 | JUPUSDT 15m | `68addd4c7d9989c9` | 12452 | 0.6347 | -100 | uno de seis | `69d410568bc6b282` | 7260 | 0.4684 | -100 | no pasa la criba |
| 25 | BTCUSDT 1h | `646edbbcb486cc0e` | 1213 | 0.6308 | -84.50 | uno de seis | `f56705d535cd11d1` | 208 | 0.5856 | -31.11 | no pasa la criba |
| 65 | SOLUSDT 15m | `21b1d3795b5045fc` | 1729 | 0.6295 | -88.09 | uno de seis | `dbc52903345e1420` | 291 | 0.4012 | -44.10 | no pasa la criba |
| 18 | JUPUSDT 5m | `c8e235e82ae1c67f` | 3029 | 0.6153 | -100 | uno de seis | `5983a250f5d96ecf` | 2143 | 0.5954 | -99.98 | no pasa la criba |
| 17 | SUIUSDT 5m | `74d466ff245e16ad` | 1603 | 0.6084 | -98.87 | uno de seis | `305294cbaf10b62d` | 561 | 0.6112 | -88.06 | no pasa la criba |
| 70 | SUIUSDT 15m | `1b3cefff7cb4c809` | 1176 | 0.6081 | -93.61 | uno de seis | `c21ce61a731d4f47` | 536 | 0.5904 | -75.13 | no pasa la criba |
| 79 | ETHUSDT 5m | `60f16dbba248bbb2` | 13845 | 0.5842 | -100 | uno de seis | `75b686713b2dbb21` | 2355 | 0.4130 | -100 | no pasa la criba |
| 51 | ETHUSDT 5m | `aff8f919c665ff3b` | 11986 | 0.5634 | -100 | uno de seis | `87ff347a7a302d3f` | 2022 | 0.4673 | -99.99 | no pasa la criba |
| 12 | JUPUSDT 15m | `29263d3ae884845d` | 99 | 0.5467 | -27.27 | uno de seis | `54d3d38a11a2731f` | 173 | 0.6802 | -29.86 | no pasa la criba |
| 42 | SUIUSDT 15m | `645dd5048c50d456` | 7526 | 0.5423 | -99.96 | uno de seis | `7e9ebb3cc3242e72` | 3335 | 0.4810 | -99.65 | no pasa la criba |
| 66 | BTCUSDT 15m | `8dcf3c24d7dddc99` | 3736 | 0.5317 | -100 | uno de seis | `bbaa090ebe0de9c4` | 600 | 0.4690 | -93.35 | no pasa la criba |
| 2 | BTCUSDT 15m | `5d07dd9aa753d5c5` | 4393 | 0.5223 | -100 | uno de seis | `d6893d70a583f23a` | 814 | 0.6174 | -91.89 | no pasa la criba |
| 13 | BTCUSDT 5m | `1b205a6408b8dda6` | 3220 | 0.5217 | -100 | uno de seis | `df041eead68e0302` | 664 | 0.5230 | -97.58 | no pasa la criba |
| 38 | BTCUSDT 5m | `f44b56aaa41bc32d` | 12049 | 0.5140 | -100 | uno de seis | `71a177501d96e7f7` | 1951 | 0.2611 | -100 | no pasa la criba |
| 61 | SUIUSDT 5m | `1be9c285c1accea3` | 870 | 0.4799 | -98.83 | uno de seis | `47235e37e77e92f3` | 354 | 0.4005 | -89.37 | no pasa la criba |
| 62 | JUPUSDT 5m | `fc446e4362a4064d` | 1425 | 0.4788 | -99.86 | uno de seis | `38b48753918d45ae` | 1117 | 0.4490 | -99.78 | no pasa la criba |
| 78 | BTCUSDT 5m | `fe1991e4c9939328` | 39181 | 0.4762 | -100 | uno de seis | `846ec917074427de` | 6481 | 0.5403 | -100 | no pasa la criba |
| 32 | ETHUSDT 5m | `ff4acbea11bda896` | 29824 | 0.4132 | -100 | uno de seis | `fae3a88cf24722f2` | 5163 | 0.4634 | -100 | no pasa la criba |
| 3 | ETHUSDT 5m | `5e630abf454ed2f7` | 14303 | 0.3514 | -100 | uno de seis | `47a18000b3ba6d76` | 2548 | 0.2879 | -100 | no pasa la criba |
| 54 | HYPEUSDT 5m | `cd6f53908add8a5d` | 83 | 0.3284 | -39.37 | uno de seis | `61148c0a672b601c` | 124 | 0.2198 | -58.22 | no pasa la criba |
| 56 | JUPUSDT 1h | `3839e9cc0cb1f4f6` | 12 | 0.2761 | -7.39 | cero de seis | `6795f899df5fcf4f` | 19 | 1.0437 | 1.02 | INSUFICIENTE MUESTRA |
| 27 | SOLUSDT 15m | `5cf50291da671435` | 11167 | 0.2508 | -100 | uno de seis | `49a4e9af6d854f2a` | 2220 | 0.1621 | -100 | no pasa la criba |
| 31 | JUPUSDT 15m | `ca275dafa85238ec` | 59 | 0.2266 | -42.59 | uno de seis | `53b3bda2d237373d` | 95 | 0.1002 | -70.14 | no pasa la criba |
| 35 | HYPEUSDT 1h | `dd48ef121acf4bb9` | 6 | 0.2235 | -3.62 | cero de seis | `39f41fbc6421d47f` | 13 | 2.1778 | 10.51 | INSUFICIENTE MUESTRA |
| 67 | ETHUSDT 15m | `89e56211b6dff829` | 28247 | 0.1986 | -100 | uno de seis | `cb0cb05a464a71a6` | 5381 | 0.2649 | -100 | no pasa la criba |
| 19 | BTCUSDT 15m | `c49ea73e2acffa35` | 57561 | 0.1462 | -100 | uno de seis | `8f470e635fc0c3f0` | 9478 | 0.2123 | -100 | no pasa la criba |
| 41 | HYPEUSDT 5m | `90b1f4fecd0a4992` | 53 | 0.0453 | -48.86 | uno de seis | `b8f46ca9905c94c5` | 63 | 2.0252 | 47.56 | no pasa la criba |
| 46 | SOLUSDT 15m | `e087e07cd10190b1` | 36 | 0 | -29.50 | uno de seis | `b0430f253a4fb123` | 10 | 0 | -9.40 | no pasa la criba |
| 49 | SUIUSDT 1h | `1baac276fc3d52f5` | 14 | 0 | -13.70 | cero de seis | `635f4c5c939e7163` | 6 | 2.6441 | 7.61 | INSUFICIENTE MUESTRA |
| 58 | BTCUSDT 1h | `18699632bac52a3a` | 3 | 0 | -3.37 | cero de seis | `973e2579b36da0eb` | 0 | 0 | 0 | INSUFICIENTE MUESTRA |
| 77 | JUPUSDT 15m | `921350a6d5fc59b2` | 0 | 0 | 0 | cero de seis | `43b7ffd26ef53120` | 0 | 0 | 0 | INSUFICIENTE MUESTRA |

## Gates, prompt por prompt (los que pasan la criba)

### #85 HYPEUSDT 1h

- DEV: artefacto `results/runs/dff8be579b3e6a87` (run_id `dff8be579b3e6a87`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 2.4884 |
| at least thirty closed trades | PASS | n = 127 |
| net return above zero | PASS | net = 26.36 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 81.71 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0721 |

- OOS: artefacto `results/runs/06774c0e8e6fcc26` (run_id `06774c0e8e6fcc26`)

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

- DEV: artefacto `results/runs/15ef339d9e9f803e` (run_id `15ef339d9e9f803e`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 2.2929 |
| at least thirty closed trades | PASS | n = 136 |
| net return above zero | PASS | net = 253.78 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 81.86 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.4387 |

- OOS: artefacto `results/runs/983185447057c499` (run_id `983185447057c499`)

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

- DEV: artefacto `results/runs/ba1affc9cac66742` (run_id `ba1affc9cac66742`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 1.3360 |
| at least thirty closed trades | PASS | n = 366 |
| net return above zero | PASS | net = 73.28 % |
| two of the three thirds green | PASS | 2 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 80.09 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0076 |

- OOS: artefacto `results/runs/62756db11ecaa1c4` (run_id `62756db11ecaa1c4`)

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

- DEV: artefacto `results/runs/e70997443c6b0aad` (run_id `e70997443c6b0aad`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 1.2622 |
| at least thirty closed trades | PASS | n = 942 |
| net return above zero | PASS | net = 319.09 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 75 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0471 |

- OOS: artefacto `results/runs/ec1d39c4f5668d89` (run_id `ec1d39c4f5668d89`)

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
| 85 | HYPEUSDT 1h | `dff8be579b3e6a87` | 127 | 2.4884 | `06774c0e8e6fcc26` | 383 | 2.9236 | 52.4 | NO CERTIFICABLE (nocional) |
| 88 | BTCUSDT 1h | `2afdfe080f5f207b` | 2433 | 1.1656 | `13cc7795bda9884b` | 368 | 1.5177 | - | no supera el veredicto |
| 90 | BASKET6 1h | `d0a5df752caf9509` | 124 | 1.1175 | `ff9398fac6aa06db` | 53 | 1.2766 | - | no supera el veredicto |
| 83 | BASKET6 1h | `46206c65ced080b8` | 125 | 1.0649 | `7fab571089dcc638` | 53 | 1.3800 | - | no supera el veredicto |
| 84 | BASKET6 1h | `a7320b9489ef4a93` | 2134 | 0.8698 | `e898ad4b562703a7` | 463 | 0.7721 | - | no supera el veredicto |
| 86 | SUIUSDT 1h | `0adc4cbb5ea1caf9` | 145 | 0.7546 | `f2deefe910c842c5` | 106 | 0.0536 | 0 | no supera el veredicto |
| 87 | BASKET6 1h | `795217d38f237c10` | 126 | 0.5675 | `257ef1cf1b118bce` | 53 | 0.4713 | - | no supera el veredicto |
| 82 | BTCUSDT 1h | `43303bde7ccc05af` | 517 | 0.3982 | `f2f0628024b793b1` | 103 | 0.1942 | 236795.5 | NO CERTIFICABLE (nocional) |
| 81 | SOLUSDT 1h | `11c4baf3008b3e40` | 215 | 0.2683 | `1ff6102761175a7c` | 44 | 0.8290 | 2940.9 | NO CERTIFICABLE (nocional) |
| 89 | ETHUSDT 15m | `c7f723c1d289476d` | 598 | 0.0855 | `d3e3ce91bbfe1f80` | 111 | 6.7333 | 1350557.5 | NO CERTIFICABLE (nocional) |

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
| 81 | SOLUSDT 1h | 2940.9 | 53969 | -18726 |
| 82 | BTCUSDT 1h | 236795.5 | 8472759 | 1167073912888322816 |
| 85 | HYPEUSDT 1h | 52.4 | 1388 | -14846 |
| 86 | SUIUSDT 1h | 0 | 2 | 0 |
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

