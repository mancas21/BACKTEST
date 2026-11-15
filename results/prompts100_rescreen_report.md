# Re-screen de los cien prompts del pack con el harness del repo

- generated: `2026-11-12`
- spec congelado antes de la primera corrida: `results/prompts100_rescreen_pre_registration.md`
- codigo del pack copiado verbatim a `code/prompts100/` con manifiesto sha256; motor del repo: `code/p100_screen_engine.py`; adapter `p100screen`
- paridad: `code/_prompts100_parity.py` (trades y metricas identicos al motor del pack); respuestas conocidas: `code/_prompts100_audit.py` (ambas direcciones)
- costes: **11 bps round trip por pierna** (5 de comision + 0.5 de slip por lado) y **funding cobrado en los settlements reales**; el invariante contable se aserta dentro de cada artefacto

## Veredicto

De los ochenta y siete prompts medidos, **cinco** limpian la criba sobre DEV y **cero** superan el veredicto completo sobre OOS (uno de los supervisivientes es pares y no es certificables: su nocional implicito no es sostenible). La razon principal no es el modelo: es el coste. El pack original corria a 2.2 bps round trip (su constante es 0.000055, o sea 0.55 bps por lado, diez veces menos de lo que documenta) y sin funding; el repo cobra 11 bps y el funding real. Ese salto es lo que separa las dos cribas.


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
| 57 | ETHUSDT 15m | `bc39cbc7d2e0b7c0` | 11 | 275.9794 | 1654.15 | 3 de 6 | `a93b1c5855394e62` | 73 | 0 | -65.25 | INSUFICIENTE MUESTRA |
| 59 | SOLUSDT 1h | `deec09f630646851` | 9 | 70.9111 | 441.64 | 4 de 6 | `6b31cf92de32e4a7` | 30 | 0.3077 | -18.62 | INSUFICIENTE MUESTRA |
| 75 | HYPEUSDT 1h | `3a2a004f27bae5f2` | 2 | 7.4868 | 5.31 | 5 de 6 | `fcb80b0801870319` | 9 | 7.0292 | 45.61 | INSUFICIENTE MUESTRA |
| 63 | BTCUSDT 15m | `2a8c8b12fa640656` | 32 | 6.7660 | 102.24 | 4 de 6 | `40ab69b1617ed120` | 32 | 0.7082 | -12.05 | no pasa la criba |
| 23 | SUIUSDT 15m | `feb32bbb8757155c` | 69 | 6.5289 | 252.68 | 4 de 6 | `0b9d356bc09ec4de` | 68 | 0.2781 | -38.48 | no pasa la criba |
| 44 | BTCUSDT 1h | `4947040db7e7fc05` | 136 | 2.2929 | 253.96 | 6 de 6 | `9d21ac54c8131fec` | 22 | 1.3816 | 5.94 | KILLED (veredicto OOS) |
| 64 | ETHUSDT 1h | `3929717a18666011` | 42 | 1.8551 | 29 | 4 de 6 | `ec3431302a8f2a59` | 15 | 0 | -15.79 | no pasa la criba |
| 29 | HYPEUSDT 15m | `d62aadbfe9c424be` | 7 | 1.5245 | 0.76 | 4 de 6 | `ed926e08dae55f37` | 36 | 3.2002 | 63.87 | INSUFICIENTE MUESTRA |
| 73 | ETHUSDT 1h | `2d777bbd78e9cb15` | 106 | 1.4692 | 36.46 | 4 de 6 | `557212148c5707e0` | 19 | 2.0567 | 8.60 | no pasa la criba |
| 22 | HYPEUSDT 1h | `42135b01bbe63fa5` | 28 | 1.3782 | 3.48 | 3 de 6 | `a17fa6a583636341` | 95 | 0.9003 | -4.30 | INSUFICIENTE MUESTRA |
| 28 | BTCUSDT 1h | `b976edc7e7b7bf82` | 366 | 1.3359 | 73.49 | 6 de 6 | `852548e0988456b0` | 63 | 0.7882 | -8.20 | KILLED (veredicto OOS) |
| 68 | SOLUSDT 1h | `c9af57f1f46c2762` | 263 | 1.3323 | 56.39 | 6 de 6 | `13d8172eae9f5212` | 52 | 0.7898 | -6.76 | KILLED (veredicto OOS) |
| 45 | ETHUSDT 1h | `5b96068f2ddf63ad` | 622 | 1.2748 | 264.63 | 5 de 6 | `fae4b728372e0dcb` | 124 | 1.0137 | 0.81 | no pasa la criba |
| 26 | ETHUSDT 1h | `ee0399ac5deab01b` | 942 | 1.2622 | 319.04 | 6 de 6 | `970ffb629bc0700e` | 183 | 1.0348 | 3.15 | KILLED (veredicto OOS) |
| 72 | BTCUSDT 1h | `973dad19d722b94d` | 317 | 1.1511 | 33.21 | 4 de 6 | `dcb86ba2330178ed` | 53 | 0.6265 | -13.18 | no pasa la criba |
| 52 | BTCUSDT 15m | `8da75fc7e69ec37d` | 877 | 1.1320 | 393.40 | 4 de 6 | `65dc234931a50b92` | 178 | 0.9920 | -1.64 | no pasa la criba |
| 60 | HYPEUSDT 1h | `58e05a39bbc0be64` | 50 | 1.0964 | 1.59 | 3 de 6 | `4f3860fa8949a7d0` | 141 | 1.3555 | 23.54 | no pasa la criba |
| 34 | SOLUSDT 1h | `73c33f84f865dc89` | 1561 | 1.0910 | 131.06 | 3 de 6 | `b68c5d621aaf139e` | 335 | 0.9596 | -8.49 | no pasa la criba |
| 21 | SOLUSDT 1h | `835440fe652b23ba` | 27 | 0.9988 | -0.25 | 0 de 6 | `10d9af47f7e7068a` | 8 | 1.5298 | 2.73 | INSUFICIENTE MUESTRA |
| 69 | HYPEUSDT 15m | `b80b028166e2d68c` | 61 | 0.9962 | -0.13 | 2 de 6 | `7a9b0fe93e52274b` | 151 | 0.7675 | -21.70 | no pasa la criba |
| 4 | HYPEUSDT 1h | `2777954b58f1d8b1` | 127 | 0.9943 | -0.86 | 2 de 6 | `9881f6d92b3f88e3` | 386 | 0.7775 | -33.95 | no pasa la criba |
| 47 | BTCUSDT 5m | `2c4f2c2433078034` | 7900 | 0.9656 | -100 | 1 de 6 | `7338e30ad8f6b0d0` | 1627 | 0.6031 | -99.98 | no pasa la criba |
| 76 | SUIUSDT 5m | `165050f55d6924a4` | 23 | 0.9639 | -0.45 | 2 de 6 | `6b03336026e448b2` | 18 | 0.9429 | -0.94 | INSUFICIENTE MUESTRA |
| 53 | SOLUSDT 5m | `1b6c239e6befdd35` | 3322 | 0.9553 | -99.42 | 1 de 6 | `6d6d437705ed8ce4` | 711 | 0.5603 | -95.40 | no pasa la criba |
| 10 | HYPEUSDT 15m | `0596d02fbb031f9f` | 213 | 0.9105 | -5.72 | 1 de 6 | `28c517812ee48fa2` | 684 | 0.8372 | -27.38 | no pasa la criba |
| 11 | SUIUSDT 1h | `9ae2f8618eeaa70a` | 171 | 0.9098 | -5.38 | 1 de 6 | `7e0548f325715542` | 79 | 0.9173 | -2.23 | no pasa la criba |
| 40 | SOLUSDT 5m | `4946c25181aab140` | 26449 | 0.9011 | -100 | 1 de 6 | `e03ff02daaea8ecd` | 5739 | 0.6651 | -100 | no pasa la criba |
| 16 | HYPEUSDT 5m | `8b83d9e71a8af604` | 759 | 0.8997 | -54.29 | 1 de 6 | `3341250838dff13e` | 1991 | 0.8406 | -97.56 | no pasa la criba |
| 7 | BTCUSDT 1h | `9fa3fda22cdaec96` | 1083 | 0.8983 | -44.23 | 1 de 6 | `00a264d8c615b947` | 138 | 0.6115 | -20.55 | no pasa la criba |
| 14 | ETHUSDT 1h | `b2437bdf32621ba5` | 742 | 0.8831 | -41.56 | 1 de 6 | `c228613cb039723e` | 106 | 0.7247 | -17.65 | no pasa la criba |
| 37 | JUPUSDT 1h | `7bf0b77a14a37ec8` | 1374 | 0.8808 | -49.48 | 1 de 6 | `465dda7967fc51b4` | 805 | 1.0100 | 2.67 | no pasa la criba |
| 33 | BTCUSDT 15m | `dd4cdf5e013b8fa8` | 7246 | 0.8319 | -100 | 1 de 6 | `93f4ae801682d95c` | 1202 | 0.5482 | -96.20 | no pasa la criba |
| 39 | ETHUSDT 15m | `e50a311d34774044` | 5735 | 0.8315 | -99.99 | 1 de 6 | `442ea6cb7b20ea18` | 996 | 0.6375 | -90.55 | no pasa la criba |
| 30 | SUIUSDT 1h | `88051b45581a47ef` | 339 | 0.8266 | -24.83 | 1 de 6 | `53e11084ab2a2b12` | 108 | 0.9149 | -4.96 | no pasa la criba |
| 1 | SOLUSDT 1h | `f4b50eec86e4dbbd` | 514 | 0.8194 | -54.72 | 1 de 6 | `ef7a3db535ed7c8b` | 123 | 0.8883 | -9.23 | no pasa la criba |
| 74 | SOLUSDT 15m | `221314b41869a764` | 1836 | 0.8135 | -81.18 | 1 de 6 | `3d6b7d65029d22fd` | 369 | 0.6721 | -47.41 | no pasa la criba |
| 50 | JUPUSDT 15m | `bcadd170937dcde9` | 12452 | 0.8067 | -100 | 1 de 6 | `a42d7c4a757804f1` | 7260 | 0.6523 | -100 | no pasa la criba |
| 80 | SOLUSDT 5m | `6e32ad102e2c0011` | 1829 | 0.8040 | -98.87 | 1 de 6 | `5c32d4af2872c170` | 361 | 0.4840 | -75.04 | no pasa la criba |
| 15 | SOLUSDT 15m | `c7fbf91860dfeacb` | 5566 | 0.8040 | -99.98 | 1 de 6 | `e1da8a67d1fcb4b2` | 1119 | 0.7380 | -89.33 | no pasa la criba |
| 6 | JUPUSDT 1h | `172f800be7d34190` | 421 | 0.8028 | -27.50 | 1 de 6 | `0db38a388ea00342` | 249 | 0.9050 | -7.47 | no pasa la criba |
| 5 | SUIUSDT 15m | `d6a174c2c6ef15bb` | 3194 | 0.7838 | -98.75 | 1 de 6 | `40f5e8f49f4bbfea` | 1274 | 0.7682 | -85.76 | no pasa la criba |
| 55 | SUIUSDT 15m | `715bfb767d210c84` | 1339 | 0.7803 | -81.03 | 1 de 6 | `35ab9885b28b7248` | 497 | 0.9502 | -18.66 | no pasa la criba |
| 24 | JUPUSDT 1h | `d9b3dbcc8055ba51` | 349 | 0.7710 | -37.36 | 1 de 6 | `3be294ac051c291c` | 174 | 0.9592 | -3.24 | no pasa la criba |
| 36 | SUIUSDT 5m | `3a6ff445510a51b2` | 2295 | 0.7642 | -93.08 | 1 de 6 | `b38b7fa71c982ffc` | 991 | 0.6347 | -97.34 | no pasa la criba |
| 48 | HYPEUSDT 15m | `d8938f22a553dfea` | 1661 | 0.7437 | -85.54 | 1 de 6 | `8e674c161218fc93` | 5082 | 0.6720 | -99.98 | no pasa la criba |
| 9 | SOLUSDT 5m | `d61de8205093e3e4` | 9420 | 0.7303 | -100 | 1 de 6 | `3c6c210d60f8476d` | 2036 | 0.6159 | -99.96 | no pasa la criba |
| 8 | ETHUSDT 15m | `3758bbef93b67016` | 5474 | 0.7270 | -100 | 1 de 6 | `fd20c557440b2e5f` | 1010 | 0.6491 | -91.13 | no pasa la criba |
| 71 | JUPUSDT 1h | `b13ec50660d0617b` | 62 | 0.6853 | -14.55 | 1 de 6 | `4fea108935d01ac5` | 43 | 1.1123 | 3.74 | no pasa la criba |
| 12 | JUPUSDT 15m | `b8e821f49d1c9993` | 99 | 0.6736 | -18.82 | 1 de 6 | `f31f526646642b4e` | 173 | 0.8998 | -9.30 | no pasa la criba |
| 70 | SUIUSDT 15m | `0f3064e8cdd28eb7` | 1176 | 0.6603 | -89.97 | 1 de 6 | `74e7003dfba38dc1` | 528 | 0.6564 | -65.35 | no pasa la criba |
| 17 | SUIUSDT 5m | `32fd912c8108b032` | 1603 | 0.6560 | -97.59 | 1 de 6 | `1221fa145eaff115` | 561 | 0.6549 | -82.99 | no pasa la criba |
| 20 | ETHUSDT 5m | `871cd231308c8be4` | 8856 | 0.6557 | -100 | 1 de 6 | `2cee743e99603124` | 1677 | 0.5990 | -99.87 | no pasa la criba |
| 65 | SOLUSDT 15m | `48c6358d29dc701a` | 1729 | 0.6505 | -86.06 | 1 de 6 | `9f18c95a5763824f` | 289 | 0.4365 | -40.96 | no pasa la criba |
| 25 | BTCUSDT 1h | `0ef47f44ded6c080` | 1213 | 0.6309 | -84.36 | 1 de 6 | `b64aaeb2b49a7dbc` | 208 | 0.5856 | -31.07 | no pasa la criba |
| 42 | SUIUSDT 15m | `df33b9049cf5c767` | 7526 | 0.6068 | -99.80 | 1 de 6 | `e1b567f969047b10` | 3304 | 0.5265 | -99.12 | no pasa la criba |
| 79 | ETHUSDT 5m | `b728abf9567af3b9` | 13845 | 0.5843 | -100 | 1 de 6 | `f794375b5eab4068` | 2355 | 0.4130 | -100 | no pasa la criba |
| 51 | ETHUSDT 5m | `2986bdde62c4b61b` | 11986 | 0.5636 | -100 | 1 de 6 | `0ec1567d913c1ebf` | 2022 | 0.4673 | -99.99 | no pasa la criba |
| 61 | SUIUSDT 5m | `18d08fb4692be862` | 870 | 0.5323 | -97.59 | 1 de 6 | `c595f86c3806d36e` | 354 | 0.4619 | -84.05 | no pasa la criba |
| 66 | BTCUSDT 15m | `284fbfad7c5eb5f8` | 3736 | 0.5317 | -100 | 1 de 6 | `247efbe827acb925` | 595 | 0.4667 | -93.65 | no pasa la criba |
| 2 | BTCUSDT 15m | `94f79f2083e187b8` | 4393 | 0.5227 | -100 | 1 de 6 | `14118c901d3dbee5` | 791 | 0.6200 | -90.59 | no pasa la criba |
| 13 | BTCUSDT 5m | `666650f93248258d` | 3220 | 0.5218 | -100 | 1 de 6 | `9c1904035aa0fbe1` | 664 | 0.5230 | -97.58 | no pasa la criba |
| 38 | BTCUSDT 5m | `26614d938de1401c` | 12049 | 0.5140 | -100 | 1 de 6 | `efc06deb61da4598` | 1951 | 0.2611 | -100 | no pasa la criba |
| 78 | BTCUSDT 5m | `2b8fa87c82f213ee` | 39181 | 0.4762 | -100 | 1 de 6 | `eb27d0f6e908b8e7` | 6481 | 0.5403 | -100 | no pasa la criba |
| 32 | ETHUSDT 5m | `b1a4b1d35af57cbb` | 29824 | 0.4132 | -100 | 1 de 6 | `9430a647d1694b93` | 5163 | 0.4634 | -100 | no pasa la criba |
| 3 | ETHUSDT 5m | `89dfee7a9844fa3a` | 14303 | 0.3515 | -100 | 1 de 6 | `6b2d41157bc43176` | 2548 | 0.2880 | -100 | no pasa la criba |
| 54 | HYPEUSDT 5m | `98f19fe2ab792644` | 83 | 0.3325 | -38.91 | 1 de 6 | `b68daa74bf095cd9` | 124 | 0.2229 | -57.96 | no pasa la criba |
| 31 | JUPUSDT 15m | `40e1fc4a98279513` | 59 | 0.2961 | -33.72 | 1 de 6 | `985b452869330cbd` | 95 | 0.1516 | -59.43 | no pasa la criba |
| 56 | JUPUSDT 1h | `631306374b9a1bfa` | 12 | 0.2832 | -7.19 | 0 de 6 | `96e4abae4b988a9f` | 19 | 1.0734 | 1.51 | INSUFICIENTE MUESTRA |
| 27 | SOLUSDT 15m | `d7ee41fa4fe2598c` | 11167 | 0.2699 | -100 | 1 de 6 | `d2a253520b206ac3` | 2199 | 0.1763 | -100 | no pasa la criba |
| 35 | HYPEUSDT 1h | `27fbde5d5390ea35` | 6 | 0.2245 | -3.62 | 0 de 6 | `e8771ba8db735b74` | 13 | 2.1810 | 10.55 | INSUFICIENTE MUESTRA |
| 67 | ETHUSDT 15m | `4a6c867ea8fc0701` | 28247 | 0.1988 | -100 | 1 de 6 | `e771e95b757127e3` | 5309 | 0.2649 | -100 | no pasa la criba |
| 19 | BTCUSDT 15m | `9b006d99a3ae1750` | 57561 | 0.1462 | -100 | 1 de 6 | `a263b65777d79f1f` | 9366 | 0.2123 | -100 | no pasa la criba |
| 41 | HYPEUSDT 5m | `95be1fba53db58e1` | 53 | 0.0459 | -48.59 | 1 de 6 | `4916290f898c9b89` | 63 | 2.0449 | 48.73 | no pasa la criba |
| 46 | SOLUSDT 15m | `0ff1a1df0213da10` | 36 | 0 | -29.20 | 1 de 6 | `af2fe940eb71663b` | 10 | 0 | -9.22 | no pasa la criba |
| 49 | SUIUSDT 1h | `67662dd7e1021a80` | 14 | 0 | -13.62 | 0 de 6 | `d3c0b19b1dfb7445` | 6 | 2.6672 | 7.71 | INSUFICIENTE MUESTRA |
| 58 | BTCUSDT 1h | `31d895d8bf640577` | 3 | 0 | -3.37 | 0 de 6 | `64f5893b48c0164e` | 0 | 0 | 0 | INSUFICIENTE MUESTRA |
| 77 | JUPUSDT 15m | `609afdf0216c944e` | 0 | 0 | 0 | 0 de 6 | `38069cf8ade8acd6` | 0 | 0 | 0 | INSUFICIENTE MUESTRA |

## Gates, prompt por prompt (los que pasan la criba)

### #85 HYPEUSDT 1h

- DEV: artefacto `results/runs/3112f5367ef0feae` (run_id `3112f5367ef0feae`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 2.6073 |
| at least thirty closed trades | PASS | n = 127 |
| net return above zero | PASS | net = 28.10 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 78.38 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0894 |

- OOS: artefacto `results/runs/b4233a3404e57ac2` (run_id `b4233a3404e57ac2`)

| gate (OOS) | resultado | medido |
|---|---|---|
| at least one hundred closed trades | PASS | n = 383 |
| profit factor ex-cost above one point two | PASS | PF = 3.0997 |
| net return above zero | PASS | net = 428.78 % |
| conc: without the five best the result is still positive | PASS | net without them = 76.25 % |
| two of the three thirds green | PASS | 3 of three green |
| the bootstrap interval above zero | PASS | CI low = 0.1152 |

- buy & hold del mismo tramo: 71.19 %; exceso del libro: 357.58 pp
- fees pagados 17414.42 USDT, funding -15312.57 USDT, resoluo del invariante 0
- **nocional implicito 52.4x el equity** (máximo 4717.9x): el libro no es certificable, y sus cifras miden la apalancamiento, no la señal

### #44 BTCUSDT 1h

- DEV: artefacto `results/runs/4947040db7e7fc05` (run_id `4947040db7e7fc05`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 2.2929 |
| at least thirty closed trades | PASS | n = 136 |
| net return above zero | PASS | net = 253.96 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 81.86 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.4225 |

- OOS: artefacto `results/runs/9d21ac54c8131fec` (run_id `9d21ac54c8131fec`)

| gate (OOS) | resultado | medido |
|---|---|---|
| at least one hundred closed trades | FAIL | n = 22 |
| profit factor ex-cost above one point two | PASS | PF = 1.3816 |
| net return above zero | PASS | net = 5.94 % |
| conc: without the five best the result is still positive | FAIL | net without them = -17.12 % |
| two of the three thirds green | FAIL | 1 of three green |
| the bootstrap interval above zero | FAIL | CI low = -0.7682 |

- buy & hold del mismo tramo: -29.09 %; exceso del libro: 35.03 pp
- fees pagados 138.61 USDT, funding 75.45 USDT, resoluo del invariante 0

### #28 BTCUSDT 1h

- DEV: artefacto `results/runs/b976edc7e7b7bf82` (run_id `b976edc7e7b7bf82`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 1.3359 |
| at least thirty closed trades | PASS | n = 366 |
| net return above zero | PASS | net = 73.49 % |
| two of the three thirds green | PASS | 2 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 80.09 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0167 |

- OOS: artefacto `results/runs/852548e0988456b0` (run_id `852548e0988456b0`)

| gate (OOS) | resultado | medido |
|---|---|---|
| at least one hundred closed trades | FAIL | n = 63 |
| profit factor ex-cost above one point two | FAIL | PF = 0.7882 |
| net return above zero | FAIL | net = -8.20 % |
| conc: without the five best the result is still positive | FAIL | net without them = -33.27 % |
| two of the three thirds green | FAIL | 1 of three green |
| the bootstrap interval above zero | FAIL | CI low = -0.5117 |

- buy & hold del mismo tramo: -29.09 %; exceso del libro: 20.89 pp
- fees pagados 373.57 USDT, funding 52.70 USDT, resoluo del invariante 0

### #68 SOLUSDT 1h

- DEV: artefacto `results/runs/c9af57f1f46c2762` (run_id `c9af57f1f46c2762`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 1.3323 |
| at least thirty closed trades | PASS | n = 263 |
| net return above zero | PASS | net = 56.39 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 77.71 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0069 |

- OOS: artefacto `results/runs/13d8172eae9f5212` (run_id `13d8172eae9f5212`)

| gate (OOS) | resultado | medido |
|---|---|---|
| at least one hundred closed trades | FAIL | n = 52 |
| profit factor ex-cost above one point two | FAIL | PF = 0.7898 |
| net return above zero | FAIL | net = -6.76 % |
| conc: without the five best the result is still positive | FAIL | net without them = -19.51 % |
| two of the three thirds green | FAIL | 1 of three green |
| the bootstrap interval above zero | FAIL | CI low = -0.5101 |

- buy & hold del mismo tramo: -49.55 %; exceso del libro: 42.80 pp
- fees pagados 238.34 USDT, funding 8.98 USDT, resoluo del invariante 0

### #26 ETHUSDT 1h

- DEV: artefacto `results/runs/ee0399ac5deab01b` (run_id `ee0399ac5deab01b`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 1.2622 |
| at least thirty closed trades | PASS | n = 942 |
| net return above zero | PASS | net = 319.04 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 75 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0471 |

- OOS: artefacto `results/runs/970ffb629bc0700e` (run_id `970ffb629bc0700e`)

| gate (OOS) | resultado | medido |
|---|---|---|
| at least one hundred closed trades | PASS | n = 183 |
| profit factor ex-cost above one point two | FAIL | PF = 1.0348 |
| net return above zero | PASS | net = 3.15 % |
| conc: without the five best the result is still positive | FAIL | net without them = -62.20 % |
| two of the three thirds green | PASS | 2 of three green |
| the bootstrap interval above zero | FAIL | CI low = -0.2649 |

- buy & hold del mismo tramo: -40.67 %; exceso del libro: 43.82 pp
- fees pagados 975.19 USDT, funding 74.81 USDT, resoluo del invariante 0

## La criba (DEV) y el veredicto (OOS): pares y cestas

Estas filas son **NO CERTIFICABLES**: el nocional implicito de su dimensionamiento no es sostenible (el tope del propio pack es 20x el equity por posicion). Se publican sus cifras measuradas, pero como **evidencia del defecto del dimensionamiento**, no como un resultado de estrategia: con esa palanca el funding, que el pack ignora, pesa mas que la senal.

| # | prompt | legs | run_id DEV | n DEV | PF DEV | run_id OOS | n OOS | PF OOS | nocional implicito (x equity) | veredicto |
|---|---|---|---|---:|---:|---|---:|---:|---:|---|
| 85 | HYPEUSDT 1h | `3112f5367ef0feae` | 127 | 2.6073 | `b4233a3404e57ac2` | 383 | 3.0997 | 52.4 | NO CERTIFICABLE (nocional) |
| 88 | BTCUSDT 1h | `f9e39e4e8418e4a1` | 2433 | 1.2442 | `64c727ce23ddafc7` | 368 | 1.6560 | - | no supera el veredicto |
| 86 | SUIUSDT 1h | `fd55df737acaa9fc` | 145 | 1.1896 | `723309555bf6ca77` | 106 | 0.0818 | 0 | no supera el veredicto |
| 90 | BASKET6 1h | `a06acac819e6df09` | 124 | 1.1430 | `29db990d09290634` | 53 | 1.3351 | - | no supera el veredicto |
| 83 | BASKET6 1h | `6407e62cfa689fb0` | 125 | 1.1080 | `2f6b8fa6799d5b17` | 53 | 1.4425 | - | no supera el veredicto |
| 84 | BASKET6 1h | `e2282bf37091bf07` | 2134 | 0.9323 | `f27908f1d59c26c1` | 463 | 0.8498 | - | no supera el veredicto |
| 87 | BASKET6 1h | `243b00fc6b5eb8f5` | 126 | 0.5699 | `59a6b649ebd109f9` | 53 | 0.4787 | - | no supera el veredicto |
| 82 | BTCUSDT 1h | `97090e800d3ced76` | 517 | 0.3982 | `294f80721bbe5c61` | 103 | 0.1942 | 236795.5 | NO CERTIFICABLE (nocional) |
| 81 | SOLUSDT 1h | `fcb141111a0da2bf` | 215 | 0.2930 | `b1f5ee2fa871d772` | 44 | 0.9159 | 2940.6 | NO CERTIFICABLE (nocional) |
| 89 | ETHUSDT 15m | `a187ab4d1fa229d8` | 598 | 0.0855 | `18280a12e277717e` | 109 | 6.9875 | 1401788.1 | NO CERTIFICABLE (nocional) |

## El control de multiplicidad

Con cien prompts cribados, la metrica OOS del ganador esta sesgada al alza: hay que distinguirse del ruido de la propia criba, no de cero. La distribucion completa de los PF de OOS de los prompts medibles se publica aqui, y un superviviente tiene que superar el percentil 95 de esa distribucion.

| prompt | PF OOS |
|---|---:|
| 89 | 6.9875 |
| 85 | 3.0997 |
| 73 | 2.0567 |
| 41 | 2.0449 |
| 88 | 1.6560 |
| 83 | 1.4425 |
| 44 | 1.3816 |
| 60 | 1.3555 |
| 90 | 1.3351 |
| 71 | 1.1123 |
| 26 | 1.0348 |
| 45 | 1.0137 |
| 37 | 1.0100 |
| 52 | 0.9920 |
| 34 | 0.9596 |
| 24 | 0.9592 |
| 55 | 0.9502 |
| 11 | 0.9173 |
| 81 | 0.9159 |
| 30 | 0.9149 |
| 6 | 0.9050 |
| 12 | 0.8998 |
| 1 | 0.8883 |
| 84 | 0.8498 |
| 16 | 0.8406 |
| 10 | 0.8372 |
| 68 | 0.7898 |
| 28 | 0.7882 |
| 4 | 0.7775 |
| 5 | 0.7682 |
| 69 | 0.7675 |
| 15 | 0.7380 |
| 14 | 0.7247 |
| 63 | 0.7082 |
| 74 | 0.6721 |
| 48 | 0.6720 |
| 40 | 0.6651 |
| 70 | 0.6564 |
| 17 | 0.6549 |
| 50 | 0.6523 |
| 8 | 0.6491 |
| 39 | 0.6375 |
| 36 | 0.6347 |
| 72 | 0.6265 |
| 2 | 0.6200 |
| 9 | 0.6159 |
| 7 | 0.6115 |
| 47 | 0.6031 |
| 20 | 0.5990 |
| 25 | 0.5856 |
| 53 | 0.5603 |
| 33 | 0.5482 |
| 78 | 0.5403 |
| 42 | 0.5265 |
| 13 | 0.5230 |
| 80 | 0.4840 |
| 87 | 0.4787 |
| 51 | 0.4673 |
| 66 | 0.4667 |
| 32 | 0.4634 |
| 61 | 0.4619 |
| 65 | 0.4365 |
| 79 | 0.4130 |
| 3 | 0.2880 |
| 23 | 0.2781 |
| 67 | 0.2649 |
| 38 | 0.2611 |
| 54 | 0.2229 |
| 19 | 0.2123 |
| 82 | 0.1942 |
| 27 | 0.1763 |
| 31 | 0.1516 |
| 86 | 0.0818 |
| 64 | 0 |
| 46 | 0 |

El percentil 95 de esa distribucion es **2.0449**. Ningun prompt lo supera: el mejor PF de OOS de la criba se queda en 6.9875.

## La familia de pares y cestas: el nocional manda

Los prompts de par (los seis de spread) no son un libro que se pueda sostener: el dimensionamiento del pack implica un **nocional bruto de decenas de miles de veces el equity**. Eso convierte el funding (que el pack no cobra) en el motor principal del resultado: con esa palanca, unos puntos de funding por settlement pesan mas que el spread. Por eso la puerta de certificabilidad es el nocional, no el profit factor.

| prompt | legs | nocional implicito (x equity) | coste sobre el nocional real por trade (USDT) | funding neto del tramo (USDT) |
|---|---|---:|---:|---:|
| 81 | SOLUSDT 1h | 2940.6 | 49496 | -18872 |
| 82 | BTCUSDT 1h | 236795.5 | 8472759 | 1167073912888322816 |
| 85 | HYPEUSDT 1h | 52.4 | 1273 | -15313 |
| 86 | SUIUSDT 1h | 0 | 1 | 0 |
| 88 | BTCUSDT 1h | - | - | 1667 |
| 89 | ETHUSDT 15m | 1401788.1 | 13221532 | 2535770 |
| 83 | BASKET6 1h | - | - | 18 |
| 84 | BASKET6 1h | - | - | 8 |
| 87 | BASKET6 1h | - | - | 85 |
| 90 | BASKET6 1h | - | - | 3 |

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

