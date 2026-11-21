# Re-screen de los cien prompts del pack con el harness del repo

- generated: `2026-11-21`
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
| 57 | ETHUSDT 15m | `ef00c4c2df464b4c` | 11 | 275.9425 | 1653.51 | tres de seis | `9729dd6345cc83f8` | 73 | 0 | -65.29 | INSUFICIENTE MUESTRA |
| 59 | SOLUSDT 1h | `d53a15547a357c4e` | 9 | 70.7753 | 441.53 | tres de seis | `5cf99975a48b8b8b` | 30 | 0.3062 | -18.75 | INSUFICIENTE MUESTRA |
| 75 | HYPEUSDT 1h | `a0c7037ea1a62b9b` | 2 | 7.4782 | 5.31 | tres de seis | `8f57ab21aa69afeb` | 9 | 7.0177 | 45.36 | INSUFICIENTE MUESTRA |
| 63 | BTCUSDT 15m | `3638eb52122b0f7a` | 32 | 6.7655 | 102.21 | cuatro de seis | `655c6b936203d3a0` | 32 | 0.2782 | -25.06 | no pasa la criba |
| 23 | SUIUSDT 15m | `3acedeafa634cbbb` | 69 | 6.3560 | 247.69 | cuatro de seis | `2b33f0d26a39a611` | 68 | 0.1294 | -46.74 | no pasa la criba |
| 44 | BTCUSDT 1h | `376cc96d5aeeb48b` | 136 | 2.2929 | 253.78 | seis de seis | `c0fddf3e7f1fb11a` | 22 | 1.3816 | 5.94 | KILLED (veredicto OOS) |
| 64 | ETHUSDT 1h | `a2c6b62bfd23600b` | 42 | 1.8551 | 28.87 | cuatro de seis | `2f558ab2e28aa107` | 15 | 0 | -15.78 | no pasa la criba |
| 29 | HYPEUSDT 15m | `e7f2a967dbf8eb70` | 7 | 1.5191 | 0.73 | tres de seis | `e86601720112fd9c` | 36 | 2.8990 | 53.91 | INSUFICIENTE MUESTRA |
| 73 | ETHUSDT 1h | `9ab125d08e484078` | 106 | 1.4695 | 36.15 | cuatro de seis | `892eb8bc31040685` | 19 | 2.0567 | 8.60 | no pasa la criba |
| 22 | HYPEUSDT 1h | `3d570bbb9eaac0d2` | 28 | 1.3719 | 3.41 | tres de seis | `81460863bb09f458` | 95 | 0.8959 | -4.51 | INSUFICIENTE MUESTRA |
| 28 | BTCUSDT 1h | `1da6ac8e8bf1f438` | 366 | 1.3360 | 73.28 | seis de seis | `530884a115e2cbbe` | 63 | 0.7882 | -8.22 | KILLED (veredicto OOS) |
| 68 | SOLUSDT 1h | `2428c17be7478c76` | 263 | 1.3253 | 55.03 | cinco de seis | `946f9b7dc04ef1c8` | 52 | 0.7832 | -7 | no pasa la criba |
| 45 | ETHUSDT 1h | `f737ff7fdb6a8340` | 622 | 1.2748 | 264.49 | cinco de seis | `c2e0cd006a185e97` | 124 | 1.0137 | 0.77 | no pasa la criba |
| 26 | ETHUSDT 1h | `303dfa1f72416ea7` | 942 | 1.2622 | 319.09 | seis de seis | `66a26ac611612a9e` | 183 | 1.0348 | 3.17 | KILLED (veredicto OOS) |
| 72 | BTCUSDT 1h | `91ad34d9ffabc027` | 317 | 1.1512 | 32.78 | cuatro de seis | `17d530b5abdd5ecd` | 53 | 0.6265 | -13.18 | no pasa la criba |
| 52 | BTCUSDT 15m | `35ddc52c2cf46351` | 877 | 1.1320 | 393.33 | cuatro de seis | `8aadc0e4d5731ce1` | 179 | 1.0705 | 13.86 | no pasa la criba |
| 60 | HYPEUSDT 1h | `86673bef8de06743` | 50 | 1.0918 | 1.48 | tres de seis | `eacfb04978181aba` | 141 | 1.3490 | 23.10 | no pasa la criba |
| 34 | SOLUSDT 1h | `73e834f27d451919` | 1561 | 1.0849 | 118.68 | tres de seis | `751e10dffa3f61e3` | 335 | 0.9492 | -10.27 | no pasa la criba |
| 21 | SOLUSDT 1h | `891ddb0a2e6c3ca0` | 27 | 0.9948 | -0.34 | cero de seis | `4c8d8d8cfb65aa5e` | 8 | 1.5191 | 2.69 | INSUFICIENTE MUESTRA |
| 4 | HYPEUSDT 1h | `10d9966e10fa7e69` | 127 | 0.9900 | -1.12 | dos de seis | `9dd103c8cfad496f` | 386 | 0.7735 | -34.57 | no pasa la criba |
| 69 | HYPEUSDT 15m | `a91e48cb6df6b2b1` | 61 | 0.9834 | -0.59 | dos de seis | `1269e8c1e575cfdb` | 151 | 0.7569 | -22.75 | no pasa la criba |
| 47 | BTCUSDT 5m | `33304dbaf16d24ce` | 7900 | 0.9657 | -100 | uno de seis | `fc6da1e0de55ceaa` | 1627 | 0.6031 | -99.98 | no pasa la criba |
| 53 | SOLUSDT 5m | `95fba4f6acb0af58` | 3322 | 0.9501 | -99.69 | uno de seis | `4f83f778395b8a6a` | 711 | 0.5416 | -96.30 | no pasa la criba |
| 7 | BTCUSDT 1h | `174d14b46dc3541b` | 1083 | 0.8985 | -44.65 | uno de seis | `441de34691b06819` | 138 | 0.6115 | -20.54 | no pasa la criba |
| 10 | HYPEUSDT 15m | `d0ca23b66f334404` | 213 | 0.8981 | -6.49 | uno de seis | `e28400c2e746d66a` | 699 | 0.8207 | -30.81 | no pasa la criba |
| 11 | SUIUSDT 1h | `12df56a8e59dc9e0` | 171 | 0.8957 | -6.23 | uno de seis | `0d5240ce4c99b714` | 79 | 0.8983 | -2.77 | no pasa la criba |
| 16 | HYPEUSDT 5m | `341ccabc373540ba` | 759 | 0.8915 | -57.43 | uno de seis | `9a287f714ca81ed6` | 1991 | 0.8328 | -98.04 | no pasa la criba |
| 76 | SUIUSDT 5m | `3c3a8e24c3b2c5e6` | 23 | 0.8911 | -1.43 | cero de seis | `5265b28f560b2c97` | 18 | 0.8933 | -1.83 | INSUFICIENTE MUESTRA |
| 14 | ETHUSDT 1h | `3a56991213b8a8fa` | 742 | 0.8831 | -41.69 | uno de seis | `87c74be67c110d3e` | 106 | 0.7247 | -17.63 | no pasa la criba |
| 40 | SOLUSDT 5m | `af4c711880aeb31c` | 26449 | 0.8794 | -100 | uno de seis | `76a9fbab96909ab6` | 5739 | 0.6457 | -100 | no pasa la criba |
| 33 | BTCUSDT 15m | `961b60b90b238a97` | 7246 | 0.8318 | -100 | uno de seis | `d5a1a9e43a2f7d85` | 1211 | 0.5479 | -96.36 | no pasa la criba |
| 39 | ETHUSDT 15m | `8b2c0034d7591b32` | 5735 | 0.8315 | -99.99 | uno de seis | `1ac035f1da4f60c8` | 1019 | 0.6361 | -91.49 | no pasa la criba |
| 1 | SOLUSDT 1h | `5198b101ab7dc1bd` | 514 | 0.8165 | -55.42 | uno de seis | `67c5d1fe3df2893a` | 123 | 0.8822 | -9.76 | no pasa la criba |
| 30 | SUIUSDT 1h | `21f5f0b87bea5b02` | 339 | 0.8142 | -26.56 | uno de seis | `595a943d9a2e9cf9` | 108 | 0.8996 | -5.87 | no pasa la criba |
| 37 | JUPUSDT 1h | `45a1e31228dbe603` | 1374 | 0.8098 | -68.62 | uno de seis | `2c62b1b69860797c` | 805 | 0.9064 | -27.07 | no pasa la criba |
| 74 | SOLUSDT 15m | `264aac8c2f613a53` | 1836 | 0.7985 | -84.14 | uno de seis | `ce0385293f3e501d` | 373 | 0.6550 | -49.98 | no pasa la criba |
| 15 | SOLUSDT 15m | `c6710058231befc6` | 5566 | 0.7955 | -99.99 | uno de seis | `5bb79408a6cffe3b` | 1143 | 0.7207 | -91.74 | no pasa la criba |
| 80 | SOLUSDT 5m | `ee28913096f65635` | 1829 | 0.7940 | -99.19 | uno de seis | `3c354bd200d38724` | 361 | 0.4574 | -77.85 | no pasa la criba |
| 55 | SUIUSDT 15m | `650645f9e7e157a5` | 1339 | 0.7581 | -84.54 | uno de seis | `bde5cdc5ef2f7679` | 503 | 0.9361 | -23.26 | no pasa la criba |
| 5 | SUIUSDT 15m | `fc04bab97ae5a438` | 3194 | 0.7446 | -99.45 | uno de seis | `11066742dcb4f784` | 1297 | 0.7271 | -91.55 | no pasa la criba |
| 6 | JUPUSDT 1h | `421e3214ae43ba41` | 421 | 0.7419 | -35.28 | uno de seis | `4739e2a5904f163e` | 249 | 0.8168 | -14.81 | no pasa la criba |
| 48 | HYPEUSDT 15m | `f2916208699afea4` | 1661 | 0.7356 | -86.74 | uno de seis | `bda2c8641a43e70d` | 5152 | 0.6636 | -99.99 | no pasa la criba |
| 8 | ETHUSDT 15m | `d26bfa9649cd53c3` | 5474 | 0.7269 | -100 | uno de seis | `f54a53863970a090` | 1034 | 0.6487 | -91.76 | no pasa la criba |
| 24 | JUPUSDT 1h | `16b125d6f61c947a` | 349 | 0.7243 | -44.19 | uno de seis | `78051eb5fc1388ac` | 174 | 0.8818 | -10 | no pasa la criba |
| 9 | SOLUSDT 5m | `4a0b7655ac3548e2` | 9420 | 0.7149 | -100 | uno de seis | `370c97803005bbb6` | 2036 | 0.5960 | -99.98 | no pasa la criba |
| 36 | SUIUSDT 5m | `d73c500f6342a342` | 2295 | 0.6884 | -97.56 | uno de seis | `d1dcf3c8d91ab289` | 991 | 0.5995 | -98.57 | no pasa la criba |
| 20 | ETHUSDT 5m | `389a19a01e455e16` | 8856 | 0.6556 | -100 | uno de seis | `27b291c493eeee98` | 1677 | 0.5990 | -99.87 | no pasa la criba |
| 71 | JUPUSDT 1h | `0df31966cb9b0fb4` | 62 | 0.6538 | -16.36 | uno de seis | `81af1ef8eaccd80d` | 43 | 1.0598 | 2.01 | no pasa la criba |
| 43 | JUPUSDT 5m | `6755ab194dd7425d` | 4708 | 0.6348 | -100 | uno de seis | `dd42720ef03762c4` | 3005 | 0.2704 | -100 | no pasa la criba |
| 50 | JUPUSDT 15m | `7be809adc5f37d4e` | 12452 | 0.6347 | -100 | uno de seis | `14abdee558f74e34` | 7260 | 0.4684 | -100 | no pasa la criba |
| 25 | BTCUSDT 1h | `a8bfab5bf9e9d66f` | 1213 | 0.6308 | -84.50 | uno de seis | `59964c7676ccce9a` | 208 | 0.5856 | -31.11 | no pasa la criba |
| 65 | SOLUSDT 15m | `8e2784634a001d8d` | 1729 | 0.6295 | -88.09 | uno de seis | `f6208513f3b8d24e` | 291 | 0.4012 | -44.10 | no pasa la criba |
| 18 | JUPUSDT 5m | `60d104451ecd88a4` | 3029 | 0.6153 | -100 | uno de seis | `be467dc1e0299839` | 2143 | 0.5954 | -99.98 | no pasa la criba |
| 17 | SUIUSDT 5m | `96a023fff66c6336` | 1603 | 0.6084 | -98.87 | uno de seis | `9752935a8ad6d5da` | 561 | 0.6112 | -88.06 | no pasa la criba |
| 70 | SUIUSDT 15m | `73f2443547391054` | 1176 | 0.6081 | -93.61 | uno de seis | `8efb05bef4951f72` | 536 | 0.5904 | -75.13 | no pasa la criba |
| 79 | ETHUSDT 5m | `1c1fb7c29d7b46fa` | 13845 | 0.5842 | -100 | uno de seis | `907fb04f9bb17441` | 2355 | 0.4130 | -100 | no pasa la criba |
| 51 | ETHUSDT 5m | `6e4ce6acaf477f9a` | 11986 | 0.5634 | -100 | uno de seis | `d26ffc510a3a11d2` | 2022 | 0.4673 | -99.99 | no pasa la criba |
| 12 | JUPUSDT 15m | `35ea135108dfc672` | 99 | 0.5467 | -27.27 | uno de seis | `fcffe26600088cac` | 173 | 0.6802 | -29.86 | no pasa la criba |
| 42 | SUIUSDT 15m | `648d1a3ccfaed620` | 7526 | 0.5423 | -99.96 | uno de seis | `3b43b86c6f5efd98` | 3335 | 0.4810 | -99.65 | no pasa la criba |
| 66 | BTCUSDT 15m | `32f54d8b0785a341` | 3736 | 0.5317 | -100 | uno de seis | `c45a86f71b315063` | 600 | 0.4690 | -93.35 | no pasa la criba |
| 2 | BTCUSDT 15m | `7167a06f4c82edca` | 4393 | 0.5223 | -100 | uno de seis | `35d8ac214fc8d69f` | 814 | 0.6174 | -91.89 | no pasa la criba |
| 13 | BTCUSDT 5m | `666353255cef9d31` | 3220 | 0.5217 | -100 | uno de seis | `64cd8f3f7989f292` | 664 | 0.5230 | -97.58 | no pasa la criba |
| 38 | BTCUSDT 5m | `a6a8d76c8d88b641` | 12049 | 0.5140 | -100 | uno de seis | `89d20d6c1190dc77` | 1951 | 0.2611 | -100 | no pasa la criba |
| 61 | SUIUSDT 5m | `3e1a70424158d1aa` | 870 | 0.4799 | -98.83 | uno de seis | `0639f94c8e9d3758` | 354 | 0.4005 | -89.37 | no pasa la criba |
| 62 | JUPUSDT 5m | `571264423c32759b` | 1425 | 0.4788 | -99.86 | uno de seis | `a641c98df5d8c5ea` | 1117 | 0.4490 | -99.78 | no pasa la criba |
| 78 | BTCUSDT 5m | `c3de81cfc00c3315` | 39181 | 0.4762 | -100 | uno de seis | `185cb48c08e99e3c` | 6481 | 0.5403 | -100 | no pasa la criba |
| 32 | ETHUSDT 5m | `800bb81a8d57b10c` | 29824 | 0.4132 | -100 | uno de seis | `7385a27141b74af2` | 5163 | 0.4634 | -100 | no pasa la criba |
| 3 | ETHUSDT 5m | `c02229ea5d987868` | 14303 | 0.3514 | -100 | uno de seis | `1f73ed947f49ccf0` | 2548 | 0.2879 | -100 | no pasa la criba |
| 54 | HYPEUSDT 5m | `ac488b0403f784c2` | 83 | 0.3284 | -39.37 | uno de seis | `1ee9b2d9a975d84a` | 124 | 0.2198 | -58.22 | no pasa la criba |
| 56 | JUPUSDT 1h | `397fb3308c64423c` | 12 | 0.2761 | -7.39 | cero de seis | `673a070e75cd0769` | 19 | 1.0437 | 1.02 | INSUFICIENTE MUESTRA |
| 27 | SOLUSDT 15m | `218495308db88f2d` | 11167 | 0.2508 | -100 | uno de seis | `fef5cb069406a572` | 2220 | 0.1621 | -100 | no pasa la criba |
| 31 | JUPUSDT 15m | `dd0121099e768eb2` | 59 | 0.2266 | -42.59 | uno de seis | `4e235c6b3dcf855f` | 95 | 0.1002 | -70.14 | no pasa la criba |
| 35 | HYPEUSDT 1h | `3f999488d7120f43` | 6 | 0.2235 | -3.62 | cero de seis | `72d1047b873ca90b` | 13 | 2.1778 | 10.51 | INSUFICIENTE MUESTRA |
| 67 | ETHUSDT 15m | `6b38c4a024650fec` | 28247 | 0.1986 | -100 | uno de seis | `e8c65ce81d171043` | 5381 | 0.2649 | -100 | no pasa la criba |
| 19 | BTCUSDT 15m | `9d910545b96de921` | 57561 | 0.1462 | -100 | uno de seis | `a576ce6c57c806d0` | 9478 | 0.2123 | -100 | no pasa la criba |
| 41 | HYPEUSDT 5m | `c17edd87b8a88eb6` | 53 | 0.0453 | -48.86 | uno de seis | `4e7bb6b8e6a2b4a0` | 63 | 2.0252 | 47.56 | no pasa la criba |
| 46 | SOLUSDT 15m | `16a3faed33ce37b2` | 36 | 0 | -29.50 | uno de seis | `61cc2a3759464054` | 10 | 0 | -9.40 | no pasa la criba |
| 49 | SUIUSDT 1h | `85d0d2ccf39e1b2f` | 14 | 0 | -13.70 | cero de seis | `a975ef86f5f7c5a5` | 6 | 2.6441 | 7.61 | INSUFICIENTE MUESTRA |
| 58 | BTCUSDT 1h | `b579428b63b1cb50` | 3 | 0 | -3.37 | cero de seis | `2b17f06a300b0382` | 0 | 0 | 0 | INSUFICIENTE MUESTRA |
| 77 | JUPUSDT 15m | `4bb537adc5385733` | 0 | 0 | 0 | cero de seis | `59c343f107924e0d` | 0 | 0 | 0 | INSUFICIENTE MUESTRA |

## Gates, prompt por prompt (los que pasan la criba)

### #85 HYPEUSDT 1h

- DEV: artefacto `results/runs/c3a368b728987ca3` (run_id `c3a368b728987ca3`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 2.4884 |
| at least thirty closed trades | PASS | n = 127 |
| net return above zero | PASS | net = 26.36 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 81.71 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0721 |

- OOS: artefacto `results/runs/0dfe18bd3555cd21` (run_id `0dfe18bd3555cd21`)

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

- DEV: artefacto `results/runs/376cc96d5aeeb48b` (run_id `376cc96d5aeeb48b`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 2.2929 |
| at least thirty closed trades | PASS | n = 136 |
| net return above zero | PASS | net = 253.78 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 81.86 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.4387 |

- OOS: artefacto `results/runs/c0fddf3e7f1fb11a` (run_id `c0fddf3e7f1fb11a`)

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

- DEV: artefacto `results/runs/1da6ac8e8bf1f438` (run_id `1da6ac8e8bf1f438`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 1.3360 |
| at least thirty closed trades | PASS | n = 366 |
| net return above zero | PASS | net = 73.28 % |
| two of the three thirds green | PASS | 2 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 80.09 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0076 |

- OOS: artefacto `results/runs/530884a115e2cbbe` (run_id `530884a115e2cbbe`)

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

- DEV: artefacto `results/runs/303dfa1f72416ea7` (run_id `303dfa1f72416ea7`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 1.2622 |
| at least thirty closed trades | PASS | n = 942 |
| net return above zero | PASS | net = 319.09 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 75 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0471 |

- OOS: artefacto `results/runs/66a26ac611612a9e` (run_id `66a26ac611612a9e`)

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
| 85 | HYPEUSDT 1h | `c3a368b728987ca3` | 127 | 2.4884 | `0dfe18bd3555cd21` | 383 | 2.9236 | 52.4 | NO CERTIFICABLE (nocional) |
| 90 | BASKET6 1h | `b8dd7d827929db21` | 124 | 1.1175 | `08b80be3a6385175` | 53 | 1.2766 | - | no supera el veredicto |
| 83 | BASKET6 1h | `67f08389b3e805e9` | 125 | 1.0649 | `ccab198ae43531f1` | 53 | 1.3800 | - | no supera el veredicto |
| 84 | BASKET6 1h | `2ea6364db738dd68` | 2134 | 0.8698 | `d5388afc96e39f2c` | 463 | 0.7721 | - | no supera el veredicto |
| 86 | SUIUSDT 1h | `c15c5b0f69129a96` | 145 | 0.7546 | `7cea0abe97805aef` | 106 | 0.0536 | 0 | no supera el veredicto |
| 87 | BASKET6 1h | `fea8e996725bd8e2` | 126 | 0.5675 | `f12c97821473a0b9` | 53 | 0.4713 | - | no supera el veredicto |
| 82 | BTCUSDT 1h | `e3f2517cae691160` | 517 | 0.3982 | `5d526ed860ee6fe4` | 103 | 0.1942 | 236795.5 | NO CERTIFICABLE (nocional) |
| 81 | SOLUSDT 1h | `97fbf434d93d0cdf` | 215 | 0.2683 | `c974863bb48a278b` | 44 | 0.8290 | 2940.9 | NO CERTIFICABLE (nocional) |
| 89 | ETHUSDT 15m | `48a06b7850a15c31` | 598 | 0.0855 | `87dc0fe82393f371` | 111 | 6.7333 | 1350557.5 | NO CERTIFICABLE (nocional) |

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

