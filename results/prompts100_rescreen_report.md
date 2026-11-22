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
| 57 | ETHUSDT 15m | `0ca6646abbe8e552` | 11 | 275.9425 | 1653.51 | tres de seis | `f81e4c9a79456938` | 73 | 0 | -65.29 | INSUFICIENTE MUESTRA |
| 59 | SOLUSDT 1h | `cd5205dfff6ea00f` | 9 | 70.7753 | 441.53 | tres de seis | `3c5de5b4ee821aa6` | 30 | 0.3062 | -18.75 | INSUFICIENTE MUESTRA |
| 75 | HYPEUSDT 1h | `97a051efa8a842b6` | 2 | 7.4782 | 5.31 | tres de seis | `c03470f106f040a5` | 9 | 7.0177 | 45.36 | INSUFICIENTE MUESTRA |
| 63 | BTCUSDT 15m | `438254c760cdb4f0` | 32 | 6.7655 | 102.21 | cuatro de seis | `d79ec573f5287706` | 32 | 0.2782 | -25.06 | no pasa la criba |
| 23 | SUIUSDT 15m | `58f83b77d5bc8a32` | 69 | 6.3560 | 247.69 | cuatro de seis | `f05abc1e06907f03` | 68 | 0.1294 | -46.74 | no pasa la criba |
| 44 | BTCUSDT 1h | `43b9379b2f5137bc` | 136 | 2.2929 | 253.78 | seis de seis | `e9cb9732474b1930` | 22 | 1.3816 | 5.94 | KILLED (veredicto OOS) |
| 64 | ETHUSDT 1h | `413914851ce459f7` | 42 | 1.8551 | 28.87 | cuatro de seis | `628df55b091da704` | 15 | 0 | -15.78 | no pasa la criba |
| 29 | HYPEUSDT 15m | `8ed5f7f523d62061` | 7 | 1.5191 | 0.73 | tres de seis | `9734fbd841b17dd0` | 36 | 2.8990 | 53.91 | INSUFICIENTE MUESTRA |
| 73 | ETHUSDT 1h | `fe727c54dbedd480` | 106 | 1.4695 | 36.15 | cuatro de seis | `2daf7c98323f68d7` | 19 | 2.0567 | 8.60 | no pasa la criba |
| 22 | HYPEUSDT 1h | `73cc25d50467812d` | 28 | 1.3719 | 3.41 | tres de seis | `82309b7290178a95` | 95 | 0.8959 | -4.51 | INSUFICIENTE MUESTRA |
| 28 | BTCUSDT 1h | `32c3af6b649d5bf7` | 366 | 1.3360 | 73.28 | seis de seis | `3d7826803b3810f3` | 63 | 0.7882 | -8.22 | KILLED (veredicto OOS) |
| 68 | SOLUSDT 1h | `ecadf4ef35d982ec` | 263 | 1.3253 | 55.03 | cinco de seis | `4a5566ed7b8a963d` | 52 | 0.7832 | -7 | no pasa la criba |
| 45 | ETHUSDT 1h | `7079875e7582fe49` | 622 | 1.2748 | 264.49 | cinco de seis | `5293bfe07e45edd2` | 124 | 1.0137 | 0.77 | no pasa la criba |
| 26 | ETHUSDT 1h | `969b1eb235593734` | 942 | 1.2622 | 319.09 | seis de seis | `9ce8e8bedb7349f3` | 183 | 1.0348 | 3.17 | KILLED (veredicto OOS) |
| 72 | BTCUSDT 1h | `658a7b7eb02d90c6` | 317 | 1.1512 | 32.78 | cuatro de seis | `c84a5355cf84d03b` | 53 | 0.6265 | -13.18 | no pasa la criba |
| 52 | BTCUSDT 15m | `7d6996ef90e322f7` | 877 | 1.1320 | 393.33 | cuatro de seis | `cdaccfe0d3cd8600` | 179 | 1.0705 | 13.86 | no pasa la criba |
| 60 | HYPEUSDT 1h | `f5bfb9efffa58537` | 50 | 1.0918 | 1.48 | tres de seis | `c39bc7f935a9c266` | 141 | 1.3490 | 23.10 | no pasa la criba |
| 34 | SOLUSDT 1h | `db36eb5a133d9b6b` | 1561 | 1.0849 | 118.68 | tres de seis | `4ceb35df57349ce4` | 335 | 0.9492 | -10.27 | no pasa la criba |
| 21 | SOLUSDT 1h | `b37703626c39081f` | 27 | 0.9948 | -0.34 | cero de seis | `608d452200af38de` | 8 | 1.5191 | 2.69 | INSUFICIENTE MUESTRA |
| 4 | HYPEUSDT 1h | `0bab17b75a16021b` | 127 | 0.9900 | -1.12 | dos de seis | `fd0266ece18b7fff` | 386 | 0.7735 | -34.57 | no pasa la criba |
| 69 | HYPEUSDT 15m | `f25ced480e436bd2` | 61 | 0.9834 | -0.59 | dos de seis | `279f35b89b2edab4` | 151 | 0.7569 | -22.75 | no pasa la criba |
| 47 | BTCUSDT 5m | `cf16561fa29f95e7` | 7900 | 0.9657 | -100 | uno de seis | `555275a344f83f67` | 1627 | 0.6031 | -99.98 | no pasa la criba |
| 53 | SOLUSDT 5m | `e9cb13fd614aec5b` | 3322 | 0.9501 | -99.69 | uno de seis | `01f6b8749ed30c4f` | 711 | 0.5416 | -96.30 | no pasa la criba |
| 7 | BTCUSDT 1h | `8e093a4c7a70b3e9` | 1083 | 0.8985 | -44.65 | uno de seis | `54cfca33dc02a227` | 138 | 0.6115 | -20.54 | no pasa la criba |
| 10 | HYPEUSDT 15m | `ace327ea33d394c7` | 213 | 0.8981 | -6.49 | uno de seis | `5f0f604b326fb786` | 699 | 0.8207 | -30.81 | no pasa la criba |
| 11 | SUIUSDT 1h | `85ecf2f398d01f47` | 171 | 0.8957 | -6.23 | uno de seis | `fb2013dce3388ad1` | 79 | 0.8983 | -2.77 | no pasa la criba |
| 16 | HYPEUSDT 5m | `77f48975ff52d415` | 759 | 0.8915 | -57.43 | uno de seis | `2ef5a75cdbbddf92` | 1991 | 0.8328 | -98.04 | no pasa la criba |
| 76 | SUIUSDT 5m | `5861c47bc58942d0` | 23 | 0.8911 | -1.43 | cero de seis | `b815179c5e3b9f57` | 18 | 0.8933 | -1.83 | INSUFICIENTE MUESTRA |
| 14 | ETHUSDT 1h | `c7dc42b47dc09bb7` | 742 | 0.8831 | -41.69 | uno de seis | `48432a3222469469` | 106 | 0.7247 | -17.63 | no pasa la criba |
| 40 | SOLUSDT 5m | `332bfa773f2e8f4f` | 26449 | 0.8794 | -100 | uno de seis | `1cc5301a749daa69` | 5739 | 0.6457 | -100 | no pasa la criba |
| 33 | BTCUSDT 15m | `4e71bfa6515d8072` | 7246 | 0.8318 | -100 | uno de seis | `925db4ee1d86e10f` | 1211 | 0.5479 | -96.36 | no pasa la criba |
| 39 | ETHUSDT 15m | `ef91e57a1abf1712` | 5735 | 0.8315 | -99.99 | uno de seis | `97afde9836e8b6d0` | 1019 | 0.6361 | -91.49 | no pasa la criba |
| 1 | SOLUSDT 1h | `f9a12e29ee878802` | 514 | 0.8165 | -55.42 | uno de seis | `c16908ff39e928a1` | 123 | 0.8822 | -9.76 | no pasa la criba |
| 30 | SUIUSDT 1h | `b63e93eb48bb8ced` | 339 | 0.8142 | -26.56 | uno de seis | `b8cbd96290230106` | 108 | 0.8996 | -5.87 | no pasa la criba |
| 37 | JUPUSDT 1h | `5656f9e9f3341cfe` | 1374 | 0.8098 | -68.62 | uno de seis | `15a51e3320c27ba2` | 805 | 0.9064 | -27.07 | no pasa la criba |
| 74 | SOLUSDT 15m | `5be50fee97cc2a2b` | 1836 | 0.7985 | -84.14 | uno de seis | `7267547e0d23aba0` | 373 | 0.6550 | -49.98 | no pasa la criba |
| 15 | SOLUSDT 15m | `fa1eac3649a9dc3f` | 5566 | 0.7955 | -99.99 | uno de seis | `f82bcf58a4c102e3` | 1143 | 0.7207 | -91.74 | no pasa la criba |
| 80 | SOLUSDT 5m | `8c0d96e292edeb10` | 1829 | 0.7940 | -99.19 | uno de seis | `9375505189071af2` | 361 | 0.4574 | -77.85 | no pasa la criba |
| 55 | SUIUSDT 15m | `4eca5be6ca603f5f` | 1339 | 0.7581 | -84.54 | uno de seis | `a6315427c8d3a2cb` | 503 | 0.9361 | -23.26 | no pasa la criba |
| 5 | SUIUSDT 15m | `7c1b9a4be8b46957` | 3194 | 0.7446 | -99.45 | uno de seis | `e5d25d909d8cdef6` | 1297 | 0.7271 | -91.55 | no pasa la criba |
| 6 | JUPUSDT 1h | `44f9af65579d94a1` | 421 | 0.7419 | -35.28 | uno de seis | `f68fec3e4cbf9531` | 249 | 0.8168 | -14.81 | no pasa la criba |
| 48 | HYPEUSDT 15m | `ae7650ff6dc79289` | 1661 | 0.7356 | -86.74 | uno de seis | `1537852de13cb863` | 5152 | 0.6636 | -99.99 | no pasa la criba |
| 8 | ETHUSDT 15m | `e65a68b67a519679` | 5474 | 0.7269 | -100 | uno de seis | `c0b9eea1f9480550` | 1034 | 0.6487 | -91.76 | no pasa la criba |
| 24 | JUPUSDT 1h | `eaf869dc90abac10` | 349 | 0.7243 | -44.19 | uno de seis | `6dab63747781c4ad` | 174 | 0.8818 | -10 | no pasa la criba |
| 9 | SOLUSDT 5m | `40c8b2a181d6a7b8` | 9420 | 0.7149 | -100 | uno de seis | `90cc0bae12773313` | 2036 | 0.5960 | -99.98 | no pasa la criba |
| 36 | SUIUSDT 5m | `7a1571af145c54fa` | 2295 | 0.6884 | -97.56 | uno de seis | `db6b5dd95e63b607` | 991 | 0.5995 | -98.57 | no pasa la criba |
| 20 | ETHUSDT 5m | `f7ac3fca2ccfb397` | 8856 | 0.6556 | -100 | uno de seis | `202e6a7880f1d021` | 1677 | 0.5990 | -99.87 | no pasa la criba |
| 71 | JUPUSDT 1h | `db054487536c2939` | 62 | 0.6538 | -16.36 | uno de seis | `c472c8215cddebbe` | 43 | 1.0598 | 2.01 | no pasa la criba |
| 43 | JUPUSDT 5m | `9773ab7b82af8feb` | 4708 | 0.6348 | -100 | uno de seis | `54c922fd8ae21a58` | 3005 | 0.2704 | -100 | no pasa la criba |
| 50 | JUPUSDT 15m | `dfbafa07ca141c7d` | 12452 | 0.6347 | -100 | uno de seis | `e059347aa1ecca71` | 7260 | 0.4684 | -100 | no pasa la criba |
| 25 | BTCUSDT 1h | `f42e661218fa747a` | 1213 | 0.6308 | -84.50 | uno de seis | `6ca0b789df7a2201` | 208 | 0.5856 | -31.11 | no pasa la criba |
| 65 | SOLUSDT 15m | `50bbc7982df9be8c` | 1729 | 0.6295 | -88.09 | uno de seis | `1a1075dabcbf7d21` | 291 | 0.4012 | -44.10 | no pasa la criba |
| 18 | JUPUSDT 5m | `b883f1f8c0d34764` | 3029 | 0.6153 | -100 | uno de seis | `9224d8fd7ce0aae7` | 2143 | 0.5954 | -99.98 | no pasa la criba |
| 17 | SUIUSDT 5m | `691d48416cf31e15` | 1603 | 0.6084 | -98.87 | uno de seis | `e77fd92c7bd3cc9b` | 561 | 0.6112 | -88.06 | no pasa la criba |
| 70 | SUIUSDT 15m | `b4b841cb342c597e` | 1176 | 0.6081 | -93.61 | uno de seis | `7c959c2c0de93fcf` | 536 | 0.5904 | -75.13 | no pasa la criba |
| 79 | ETHUSDT 5m | `ce300d535abd27ef` | 13845 | 0.5842 | -100 | uno de seis | `dfbcb98d42714835` | 2355 | 0.4130 | -100 | no pasa la criba |
| 51 | ETHUSDT 5m | `e29121d02ce6540b` | 11986 | 0.5634 | -100 | uno de seis | `204a97127b7b35ff` | 2022 | 0.4673 | -99.99 | no pasa la criba |
| 12 | JUPUSDT 15m | `f3eba9c07aca220f` | 99 | 0.5467 | -27.27 | uno de seis | `4aa24b48b06ba910` | 173 | 0.6802 | -29.86 | no pasa la criba |
| 42 | SUIUSDT 15m | `8e9f46c829575335` | 7526 | 0.5423 | -99.96 | uno de seis | `3cc40128d682751b` | 3335 | 0.4810 | -99.65 | no pasa la criba |
| 66 | BTCUSDT 15m | `8fc5fde3c1f84a0c` | 3736 | 0.5317 | -100 | uno de seis | `5a5394fb69325afb` | 600 | 0.4690 | -93.35 | no pasa la criba |
| 2 | BTCUSDT 15m | `394a4410935b1f36` | 4393 | 0.5223 | -100 | uno de seis | `c0275cb2b493be4d` | 814 | 0.6174 | -91.89 | no pasa la criba |
| 13 | BTCUSDT 5m | `277f1c3f10f6a493` | 3220 | 0.5217 | -100 | uno de seis | `7e1db99735c674e8` | 664 | 0.5230 | -97.58 | no pasa la criba |
| 38 | BTCUSDT 5m | `910dc3601b785dec` | 12049 | 0.5140 | -100 | uno de seis | `783d21cb1910848a` | 1951 | 0.2611 | -100 | no pasa la criba |
| 61 | SUIUSDT 5m | `b47ca8ba0e190d39` | 870 | 0.4799 | -98.83 | uno de seis | `5073c4bddceef10a` | 354 | 0.4005 | -89.37 | no pasa la criba |
| 62 | JUPUSDT 5m | `4da7714a40aabcbf` | 1425 | 0.4788 | -99.86 | uno de seis | `95b061ec8b25a4a4` | 1117 | 0.4490 | -99.78 | no pasa la criba |
| 78 | BTCUSDT 5m | `3900fe7a4c67cfec` | 39181 | 0.4762 | -100 | uno de seis | `897c3ccc9bab5b95` | 6481 | 0.5403 | -100 | no pasa la criba |
| 32 | ETHUSDT 5m | `2aebbd74e1d663be` | 29824 | 0.4132 | -100 | uno de seis | `fa646a7369ec5202` | 5163 | 0.4634 | -100 | no pasa la criba |
| 3 | ETHUSDT 5m | `5587d0c4e11b5a9d` | 14303 | 0.3514 | -100 | uno de seis | `56ba3e35486ef90f` | 2548 | 0.2879 | -100 | no pasa la criba |
| 54 | HYPEUSDT 5m | `5d62fa2f36ed4b84` | 83 | 0.3284 | -39.37 | uno de seis | `ca78bd2e3c4ffbca` | 124 | 0.2198 | -58.22 | no pasa la criba |
| 56 | JUPUSDT 1h | `fad42f38d4e2e7f8` | 12 | 0.2761 | -7.39 | cero de seis | `f392b8811f07aae0` | 19 | 1.0437 | 1.02 | INSUFICIENTE MUESTRA |
| 27 | SOLUSDT 15m | `40624a1074ae1568` | 11167 | 0.2508 | -100 | uno de seis | `643fca46e3db4f4d` | 2220 | 0.1621 | -100 | no pasa la criba |
| 31 | JUPUSDT 15m | `2dd902f5d3400537` | 59 | 0.2266 | -42.59 | uno de seis | `117213b5ee076744` | 95 | 0.1002 | -70.14 | no pasa la criba |
| 35 | HYPEUSDT 1h | `6e00daba689f79da` | 6 | 0.2235 | -3.62 | cero de seis | `c87b2f6eacfe104c` | 13 | 2.1778 | 10.51 | INSUFICIENTE MUESTRA |
| 67 | ETHUSDT 15m | `c028b830478d567d` | 28247 | 0.1986 | -100 | uno de seis | `7a63481ecd525cd8` | 5381 | 0.2649 | -100 | no pasa la criba |
| 19 | BTCUSDT 15m | `91ccecaf5a80f34b` | 57561 | 0.1462 | -100 | uno de seis | `41708095b3e142fb` | 9478 | 0.2123 | -100 | no pasa la criba |
| 41 | HYPEUSDT 5m | `ca24bb51fb325340` | 53 | 0.0453 | -48.86 | uno de seis | `b04d246235481431` | 63 | 2.0252 | 47.56 | no pasa la criba |
| 46 | SOLUSDT 15m | `f25b51e5deb89843` | 36 | 0 | -29.50 | uno de seis | `ed5a64552c640e96` | 10 | 0 | -9.40 | no pasa la criba |
| 49 | SUIUSDT 1h | `d9d7227c323894b9` | 14 | 0 | -13.70 | cero de seis | `fba0566c9a14f81c` | 6 | 2.6441 | 7.61 | INSUFICIENTE MUESTRA |
| 58 | BTCUSDT 1h | `d6c1b0bcdf124b94` | 3 | 0 | -3.37 | cero de seis | `c0903d6ae215891f` | 0 | 0 | 0 | INSUFICIENTE MUESTRA |
| 77 | JUPUSDT 15m | `a9607d5677066bef` | 0 | 0 | 0 | cero de seis | `84bcf7886b9ea726` | 0 | 0 | 0 | INSUFICIENTE MUESTRA |

## Gates, prompt por prompt (los que pasan la criba)

### #85 HYPEUSDT 1h

- DEV: artefacto `results/runs/99dd566e2a4f7372` (run_id `99dd566e2a4f7372`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 2.4884 |
| at least thirty closed trades | PASS | n = 127 |
| net return above zero | PASS | net = 26.36 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 81.71 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0721 |

- OOS: artefacto `results/runs/a2c8b1bcd08e1254` (run_id `a2c8b1bcd08e1254`)

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

- DEV: artefacto `results/runs/43b9379b2f5137bc` (run_id `43b9379b2f5137bc`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 2.2929 |
| at least thirty closed trades | PASS | n = 136 |
| net return above zero | PASS | net = 253.78 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 81.86 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.4387 |

- OOS: artefacto `results/runs/e9cb9732474b1930` (run_id `e9cb9732474b1930`)

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

- DEV: artefacto `results/runs/32c3af6b649d5bf7` (run_id `32c3af6b649d5bf7`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 1.3360 |
| at least thirty closed trades | PASS | n = 366 |
| net return above zero | PASS | net = 73.28 % |
| two of the three thirds green | PASS | 2 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 80.09 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0076 |

- OOS: artefacto `results/runs/3d7826803b3810f3` (run_id `3d7826803b3810f3`)

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

- DEV: artefacto `results/runs/969b1eb235593734` (run_id `969b1eb235593734`)

| gate (DEV) | resultado | medido |
|---|---|---|
| profit factor ex-cost above one point two | PASS | PF = 1.2622 |
| at least thirty closed trades | PASS | n = 942 |
| net return above zero | PASS | net = 319.09 % |
| two of the three thirds green | PASS | 3 of three green |
| the five best trades at most one hundred per cent of the PnL | PASS | best five = 75 % of PnL |
| the bootstrap interval above zero | PASS | CI low = 0.0471 |

- OOS: artefacto `results/runs/9ce8e8bedb7349f3` (run_id `9ce8e8bedb7349f3`)

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
| 85 | HYPEUSDT 1h | `99dd566e2a4f7372` | 127 | 2.4884 | `a2c8b1bcd08e1254` | 383 | 2.9236 | 52.4 | NO CERTIFICABLE (nocional) |
| 90 | BASKET6 1h | `360dedf97e6fa808` | 124 | 1.1175 | `6793e24459d2e192` | 53 | 1.2766 | - | no supera el veredicto |
| 83 | BASKET6 1h | `d0de81e995439758` | 125 | 1.0649 | `b20742134f8d6bc2` | 53 | 1.3800 | - | no supera el veredicto |
| 84 | BASKET6 1h | `7e331c29ba1cf6e8` | 2134 | 0.8698 | `b9d3eedd49de4c16` | 463 | 0.7721 | - | no supera el veredicto |
| 86 | SUIUSDT 1h | `b584e3018e628540` | 145 | 0.7546 | `b7980ec0b58cff5a` | 106 | 0.0536 | 0 | no supera el veredicto |
| 87 | BASKET6 1h | `00b73f3eb88ae16a` | 126 | 0.5675 | `0954f965f8a861f2` | 53 | 0.4713 | - | no supera el veredicto |
| 82 | BTCUSDT 1h | `8ef6a8ddc4cc19e5` | 517 | 0.3982 | `0cb9667f8ed648be` | 103 | 0.1942 | 236795.5 | NO CERTIFICABLE (nocional) |
| 81 | SOLUSDT 1h | `1a2037bd346bb097` | 215 | 0.2683 | `28d04c210974d3bf` | 44 | 0.8290 | 2940.9 | NO CERTIFICABLE (nocional) |
| 89 | ETHUSDT 15m | `29f449b9b0815494` | 598 | 0.0855 | `41c073e692470169` | 111 | 6.7333 | 1350557.5 | NO CERTIFICABLE (nocional) |

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

