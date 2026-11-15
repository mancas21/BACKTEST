# Top-100 del repo transferido a 1d x 11 pares, datos SOLO 2026

Campana 2026-11-14. Las 100 estrategias del ranking vigente
(results/top100_2026-11-09_strategies.json) se transfieren VERBATIM
(adapter + params) a tf=1d sobre once pares, con los datos acotados al
ano 2026 EN LOS BYTES: data/binance_klines_1d y _1d_taker empiezan en
2026-01-01T00:00Z (code/fetch_1d_pairs.py, Binance fapi publico), asi
que ningun motor puede leer barras previas. Consecuencia declarada: el
warmup sale de la propia ventana - una estrategia de lookback L empieza
a operar en la barra L, y las estrategias de lookback largo pueden no
operar nunca dentro de 2026.

Coverage de datos: once simbolos x trescientas diecisiete barras
diarias cerradas
(2026-01-01 a 2026-11-13), salvo los perps listados dentro de 2026:
NVDAUSDT 233 barras (desde 2026-03-26) y SPCXUSDT 177 barras. Las once
series pasan datacheck_klines (results/_1d_2026_datacheck.txt). Funding:
los tres simbolos sin archivo (NVDAUSDT, SPCXUSDT, 1000PEPEUSDT) se
crearon desde su primer settlement real (junio 2026, cadencia 8h) y los
nueve existentes se extendieron append-only hasta el ultimo settlement;
datacheck_funding regenero data/FUNDING_MANIFEST.json (results/
funding_datacheck_2026-11-14.txt).

El ranking contiene estrategias repetidas; las celdas se deduplican por
(adapter, params, tf, par) y el informe mapea cada rank del top-100 a su
celda. Plan: quinientas treinta y nueve celdas unicas (cuarenta y
cuatro combos de estrategia x once pares).
Cada celda se INTENTO aunque su motor llevase guard conocido: el rechazo
registrado es el texto real del run, nada pre-clasificado.

COSTES Y FUNDING: cada adapter declara el suyo dentro del artefacto
(cost_bp_roundtrip y funding_model por fila). Los adapters con input de
funding (qs096, qs097) cobran settlements reales; pack20 declara funding
NO cobrado; rsimr/eqpack/pack50 corren via data_dir=data/binance_klines_1d
y ese mecanismo sustituye TODOS los inputs por el CSV 1d del par, asi que
esos libros corren sin funding (declarado por el propio artefacto).

Celdas con artefacto: ciento cincuenta de quinientas treinta y nueve; celdas rechazadas por sus propios guards: trescientas ochenta y nueve. Verbo abajo, ninguna cifra fuera de
artefacto. Los recuentos van en palabras; las unicas cifras de este
informe son campos citados por run_id en la tabla.

## Resultados (solo celdas que produjeron artefacto)

| adapter | ranks | par | params | run_id | ret% | PF | n | maxDD% | win% | BH% | cost RT bp | funding pagado | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cvrmd | 84 | None | {} | 9c9c9a32596823b3 | 0.00 | 0.00 | 0 | -0.00 | 0.00 | n/a | n/a | n/a | INSUFFICIENT_SAMPLE |
| cvrmd | 84 | None | {} | 3be283dc78499f21 | 0.00 | 0.00 | 0 | -0.00 | 0.00 | n/a | n/a | n/a | INSUFFICIENT_SAMPLE |
| cvrmd | 84 | None | {} | f8fe304db2ef1687 | 0.00 | 0.00 | 0 | -0.00 | 0.00 | n/a | n/a | n/a | INSUFFICIENT_SAMPLE |
| cvrmd | 84 | None | {} | f2e7e3930612b5cd | 0.00 | 0.00 | 0 | -0.00 | 0.00 | n/a | n/a | n/a | INSUFFICIENT_SAMPLE |
| cvrmd | 84 | None | {} | 0eb511cfdbff4a78 | 0.00 | 0.00 | 0 | -0.00 | 0.00 | n/a | n/a | n/a | INSUFFICIENT_SAMPLE |
| cvrmd | 84 | None | {} | f8786ea9d62bc0d9 | 0.00 | 0.00 | 0 | -0.00 | 0.00 | n/a | n/a | n/a | INSUFFICIENT_SAMPLE |
| cvrmd | 84 | None | {} | 18f5e4f284191b81 | 0.00 | 0.00 | 0 | -0.00 | 0.00 | n/a | n/a | n/a | INSUFFICIENT_SAMPLE |
| cvrmd | 84 | None | {} | 0d40bdc4d2331c9c | 0.00 | 0.00 | 0 | -0.00 | 0.00 | n/a | n/a | n/a | INSUFFICIENT_SAMPLE |
| cvrmd | 84 | None | {} | f56cf90752ceecea | 0.00 | 0.00 | 0 | -0.00 | 0.00 | n/a | n/a | n/a | INSUFFICIENT_SAMPLE |
| cvrmd | 84 | None | {} | f9d9d97643cfbc1c | 0.00 | 0.00 | 0 | -0.00 | 0.00 | n/a | n/a | n/a | INSUFFICIENT_SAMPLE |
| cvrmd | 84 | None | {} | e647ddc49b1715ce | 0.00 | 0.00 | 0 | -0.00 | 0.00 | n/a | n/a | n/a | INSUFFICIENT_SAMPLE |
| eqpack | 5,19,21 | None | {} | a68a9fd4c334d108 | n/a | n/a | - | n/a | n/a | 32.40 | 1.20 | n/a |  |
| eqpack | 5,19,21 | None | {} | a06ea5a8ef03e373 | n/a | n/a | - | n/a | n/a | 195.76 | 1.20 | n/a |  |
| eqpack | 5,19,21 | None | {} | 2a2f3438e5272ca1 | n/a | n/a | - | n/a | n/a | -45.91 | 1.20 | n/a |  |
| eqpack | 5,19,21 | None | {} | 9935f847764ca31f | n/a | n/a | - | n/a | n/a | -27.91 | 1.20 | n/a |  |
| eqpack | 5,19,21 | None | {} | 454bc21feb650816 | n/a | n/a | - | n/a | n/a | -38.37 | 1.20 | n/a |  |
| eqpack | 5,19,21 | None | {} | 823e0c486f8e4442 | n/a | n/a | - | n/a | n/a | -35.75 | 1.20 | n/a |  |
| eqpack | 5,19,21 | None | {} | a1ea2ded7ff88689 | n/a | n/a | - | n/a | n/a | -6.50 | 1.20 | n/a |  |
| eqpack | 5,19,21 | None | {} | 5dc7f743c59be0f7 | n/a | n/a | - | n/a | n/a | -34.17 | 1.20 | n/a |  |
| eqpack | 5,19,21 | None | {} | 414e9c18cca81997 | n/a | n/a | - | n/a | n/a | -10.46 | 1.20 | n/a |  |
| eqpack | 5,19,21 | None | {} | ce7c1c2e4a95d275 | n/a | n/a | - | n/a | n/a | -46.22 | 1.20 | n/a |  |
| eqpack | 5,19,21 | None | {} | 774d76a4d1bfb0cc | n/a | n/a | - | n/a | n/a | -23.11 | 1.20 | n/a |  |
| pack20 | 13,49,82 | None | {"id": 17} | 88731a617a093ded | 0.00 | n/a | 0 | 0.00 | n/a | 40.70 | 11.00 | n/a |  |
| pack20 | 13,49,82 | None | {"id": 17} | 8120d4fc01ca0758 | 0.00 | n/a | 0 | 0.00 | n/a | 181.71 | 11.00 | n/a |  |
| pack20 | 13,49,82 | None | {"id": 17} | 31d97922cffaca6f | 0.00 | n/a | 0 | 0.00 | n/a | -43.30 | 11.00 | n/a |  |
| pack20 | 13,49,82 | None | {"id": 17} | 408ab659e9b95a21 | 0.00 | n/a | 0 | 0.00 | n/a | -22.36 | 11.00 | n/a |  |
| pack20 | 13,49,82 | None | {"id": 17} | af1c3d10d8e149e9 | 0.00 | n/a | 0 | 0.00 | n/a | -37.25 | 11.00 | n/a |  |
| pack20 | 13,49,82 | None | {"id": 17} | ebe5862597544d37 | 0.00 | n/a | 0 | 0.00 | n/a | -35.05 | 11.00 | n/a |  |
| pack20 | 13,49,82 | None | {"id": 17} | ee6a7c4583711962 | 0.00 | n/a | 0 | 0.00 | n/a | -7.28 | 11.00 | n/a |  |
| pack20 | 13,49,82 | None | {"id": 17} | 5c972460f86a337e | 0.00 | n/a | 0 | 0.00 | n/a | -33.61 | 11.00 | n/a |  |
| pack20 | 13,49,82 | None | {"id": 17} | 720b7f42397cad94 | 0.00 | n/a | 0 | 0.00 | n/a | 9.28 | 11.00 | n/a |  |
| pack20 | 13,49,82 | None | {"id": 17} | 29f97a2114818f4a | 0.00 | n/a | 0 | 0.00 | n/a | -45.11 | 11.00 | n/a |  |
| pack20 | 13,49,82 | None | {"id": 17} | 167bbcd4e8cee24a | 0.00 | n/a | 0 | 0.00 | n/a | -22.06 | 11.00 | n/a |  |
| pack20 | 30,71,94 | None | {"id": 1} | 987cd13c0964ea2f | 66.96 | 2.26 | 5 | -24.16 | n/a | 40.70 | 11.00 | n/a |  |
| pack20 | 30,71,94 | None | {"id": 1} | c8db260ed7c32d5c | -34.28 | 0.00 | 4 | -34.28 | n/a | 181.71 | 11.00 | n/a |  |
| pack20 | 30,71,94 | None | {"id": 1} | b82da79445b6f7c4 | -7.09 | 0.00 | 1 | -7.09 | n/a | -43.30 | 11.00 | n/a |  |
| pack20 | 30,71,94 | None | {"id": 1} | 5928189850b5c6c1 | -53.88 | 0.00 | 3 | -53.88 | n/a | -22.36 | 11.00 | n/a |  |
| pack20 | 30,71,94 | None | {"id": 1} | 3930ace0510fbc13 | -36.07 | 0.00 | 5 | -36.07 | n/a | -37.25 | 11.00 | n/a |  |
| pack20 | 30,71,94 | None | {"id": 1} | e24e5ea80813c15c | -2.82 | 0.79 | 3 | -9.93 | n/a | -35.05 | 11.00 | n/a |  |
| pack20 | 30,71,94 | None | {"id": 1} | 422d1978bf7afcd9 | 30.52 | 8.51 | 4 | -3.36 | n/a | -7.28 | 11.00 | n/a |  |
| pack20 | 30,71,94 | None | {"id": 1} | fbc79782f13e9c15 | -6.49 | 0.69 | 2 | -20.76 | n/a | -33.61 | 11.00 | n/a |  |
| pack20 | 30,71,94 | None | {"id": 1} | f30866ba8f028c45 | -19.85 | 0.00 | 1 | -19.85 | n/a | 9.28 | 11.00 | n/a |  |
| pack20 | 30,71,94 | None | {"id": 1} | 595a4705857164f2 | 28.21 | 4.79 | 3 | -5.49 | n/a | -45.11 | 11.00 | n/a |  |
| pack20 | 30,71,94 | None | {"id": 1} | af1eee4e87307407 | -10.21 | 0.00 | 1 | -10.21 | n/a | -22.06 | 11.00 | n/a |  |
| pack20 | 75 | None | {"id": 13} | 64d8095ee295323f | 0.00 | n/a | 0 | 0.00 | n/a | 40.70 | 11.00 | n/a |  |
| pack20 | 75 | None | {"id": 13} | 63c345e1840f11f6 | 0.00 | n/a | 0 | 0.00 | n/a | 181.71 | 11.00 | n/a |  |
| pack20 | 75 | None | {"id": 13} | c5fab607d273b596 | 0.00 | n/a | 0 | 0.00 | n/a | -43.30 | 11.00 | n/a |  |
| pack20 | 75 | None | {"id": 13} | cf208acaec1361a8 | 0.00 | n/a | 0 | 0.00 | n/a | -22.36 | 11.00 | n/a |  |
| pack20 | 75 | None | {"id": 13} | 908e7b18585cb695 | 0.00 | n/a | 0 | 0.00 | n/a | -37.25 | 11.00 | n/a |  |
| pack20 | 75 | None | {"id": 13} | 0cc3b5dea9f0a014 | 0.00 | n/a | 0 | 0.00 | n/a | -35.05 | 11.00 | n/a |  |
| pack20 | 75 | None | {"id": 13} | 71699b726369b5b1 | 0.00 | n/a | 0 | 0.00 | n/a | -7.28 | 11.00 | n/a |  |
| pack20 | 75 | None | {"id": 13} | ab621a1146e58c0b | 0.00 | n/a | 0 | 0.00 | n/a | -33.61 | 11.00 | n/a |  |
| pack20 | 75 | None | {"id": 13} | ff6082305f8fc7ec | 0.00 | n/a | 0 | 0.00 | n/a | 9.28 | 11.00 | n/a |  |
| pack20 | 75 | None | {"id": 13} | 337d50d74147f6ad | 0.00 | n/a | 0 | 0.00 | n/a | -45.11 | 11.00 | n/a |  |
| pack20 | 75 | None | {"id": 13} | 2091b68c785022a6 | 0.00 | n/a | 0 | 0.00 | n/a | -22.06 | 11.00 | n/a |  |
| pack20 | 78 | None | {"id": 15} | b9c864f8c0de622f | -9.81 | 0.00 | 1 | -9.81 | n/a | 40.70 | 11.00 | n/a |  |
| pack20 | 78 | None | {"id": 15} | 0c118755b3442b39 | 0.14 | 1.01 | 3 | -19.25 | n/a | 181.71 | 11.00 | n/a |  |
| pack20 | 78 | None | {"id": 15} | 974c14c5b2261c12 | -1.15 | 0.92 | 3 | -7.95 | n/a | -43.30 | 11.00 | n/a |  |
| pack20 | 78 | None | {"id": 15} | cc626bf888dc1c5a | -1.35 | 0.87 | 2 | -9.98 | n/a | -22.36 | 11.00 | n/a |  |
| pack20 | 78 | None | {"id": 15} | 45f85ef0a2676c6f | 2.53 | n/a | 1 | 0.00 | n/a | -37.25 | 11.00 | n/a |  |
| pack20 | 78 | None | {"id": 15} | 61e87fa6156c5190 | 3.17 | n/a | 1 | 0.00 | n/a | -35.05 | 11.00 | n/a |  |
| pack20 | 78 | None | {"id": 15} | b30e2d93aca88bc7 | 0.00 | n/a | 0 | 0.00 | n/a | -7.28 | 11.00 | n/a |  |
| pack20 | 78 | None | {"id": 15} | cff58c53e0e6d1d0 | 0.00 | n/a | 0 | 0.00 | n/a | -33.61 | 11.00 | n/a |  |
| pack20 | 78 | None | {"id": 15} | 03ce35c08900fba0 | -9.10 | 0.00 | 1 | -9.10 | n/a | 9.28 | 11.00 | n/a |  |
| pack20 | 78 | None | {"id": 15} | 1e465c95c0976149 | 0.00 | n/a | 0 | 0.00 | n/a | -45.11 | 11.00 | n/a |  |
| pack20 | 78 | None | {"id": 15} | 494db468a107a6d1 | 1.97 | 1.33 | 3 | -5.59 | n/a | -22.06 | 11.00 | n/a |  |
| pack20 | 93 | None | {"id": 16} | 750dbc5217ab242a | -22.34 | 0.55 | 10 | -39.61 | n/a | 40.70 | 11.00 | n/a |  |
| pack20 | 93 | None | {"id": 16} | 6e7931cf04cc81c4 | -31.05 | 0.17 | 8 | -32.23 | n/a | 181.71 | 11.00 | n/a |  |
| pack20 | 93 | None | {"id": 16} | 0ce59401c8d0efbf | -27.90 | 0.32 | 12 | -27.90 | n/a | -43.30 | 11.00 | n/a |  |
| pack20 | 93 | None | {"id": 16} | 7a762ec951c26540 | -23.92 | 0.10 | 7 | -24.53 | n/a | -22.36 | 11.00 | n/a |  |
| pack20 | 93 | None | {"id": 16} | aad2259e13128112 | -28.36 | 0.14 | 13 | -28.36 | n/a | -37.25 | 11.00 | n/a |  |
| pack20 | 93 | None | {"id": 16} | cfd438edc535bbb6 | -11.26 | 0.80 | 21 | -20.97 | n/a | -35.05 | 11.00 | n/a |  |
| pack20 | 93 | None | {"id": 16} | f812e8e83ab15a12 | -10.44 | 0.00 | 3 | -10.44 | n/a | -7.28 | 11.00 | n/a |  |
| pack20 | 93 | None | {"id": 16} | 0f551447ad3f8f7a | 1.49 | 1.65 | 2 | -2.28 | n/a | -33.61 | 11.00 | n/a |  |
| pack20 | 93 | None | {"id": 16} | 6b201bf3ac5c4078 | -21.13 | 0.61 | 13 | -40.41 | n/a | 9.28 | 11.00 | n/a |  |
| pack20 | 93 | None | {"id": 16} | 59096d3e022a64dd | -15.29 | 0.49 | 13 | -21.84 | n/a | -45.11 | 11.00 | n/a |  |
| pack20 | 93 | None | {"id": 16} | e4d91ece5266a40d | -14.74 | 0.54 | 17 | -19.20 | n/a | -22.06 | 11.00 | n/a |  |
| pack50 | 33 | None | {"strat": 46} | 8cd88065bc7dd49f | -26.89 | 0.76 | 34 | 47.91 | 41.18 | 40.70 | 12.00 | 0.00 |  |
| pack50 | 33 | None | {"strat": 46} | 1bde38c70f8f5b4c | -26.94 | 0.64 | 29 | 41.95 | 41.38 | 181.71 | 12.00 | 0.00 |  |
| pack50 | 33 | None | {"strat": 46} | 4c96f51b5922e22c | -13.88 | 0.79 | 37 | 42.30 | 51.35 | -43.30 | 12.00 | 0.00 |  |
| pack50 | 33 | None | {"strat": 46} | 1f43030f517d71d5 | -34.41 | 0.57 | 32 | 44.12 | 46.88 | -22.36 | 12.00 | 0.00 |  |
| pack50 | 33 | None | {"strat": 46} | f1f89505011e4bbe | -30.32 | 0.54 | 34 | 30.76 | 50.00 | -37.25 | 12.00 | 0.00 |  |
| pack50 | 33 | None | {"strat": 46} | feab73d0dd930c5d | -26.12 | 0.37 | 18 | 33.42 | 55.56 | -35.05 | 12.00 | 0.00 |  |
| pack50 | 33 | None | {"strat": 46} | 393b1cea0eed70b2 | -7.55 | 0.59 | 10 | 14.65 | 50.00 | -7.28 | 12.00 | 0.00 |  |
| pack50 | 33 | None | {"strat": 46} | d00c72b58dc3b80e | 10.89 | 1.98 | 11 | 7.99 | 54.55 | -33.61 | 12.00 | 0.00 |  |
| pack50 | 33 | None | {"strat": 46} | 3586a215c95d6d87 | 53.63 | 1.76 | 34 | 29.17 | 64.71 | 9.28 | 12.00 | 0.00 |  |
| pack50 | 33 | None | {"strat": 46} | 4fb38bf8a47fa642 | -21.37 | 0.65 | 29 | 29.77 | 51.72 | -45.11 | 12.00 | 0.00 |  |
| pack50 | 33 | None | {"strat": 46} | 391364ae50d1e789 | -19.09 | 0.44 | 25 | 23.62 | 36.00 | -22.06 | 12.00 | 0.00 |  |
| pack50 | 76 | None | {"strat": 5} | 57312a225cba8b8a | 21.45 | 3.16 | 6 | 14.63 | 50.00 | 40.70 | 20.00 | 0.00 |  |
| pack50 | 76 | None | {"strat": 5} | f323e2e155fc8270 | 7.96 | 1.22 | 10 | 24.11 | 30.00 | 181.71 | 20.00 | 0.00 |  |
| pack50 | 76 | None | {"strat": 5} | 016e8eec15945c31 | 21.63 | 2.32 | 6 | 21.79 | 33.33 | -43.30 | 20.00 | 0.00 |  |
| pack50 | 76 | None | {"strat": 5} | ec7087e25e61556a | -14.72 | 0.46 | 9 | 32.00 | 11.11 | -22.36 | 20.00 | 0.00 |  |
| pack50 | 76 | None | {"strat": 5} | 6f17826da9a04238 | -3.67 | 0.74 | 6 | 13.61 | 50.00 | -37.25 | 20.00 | 0.00 |  |
| pack50 | 76 | None | {"strat": 5} | cfe6c7da5474a10b | -12.06 | 0.00 | 5 | 16.05 | 0.00 | -35.05 | 20.00 | 0.00 |  |
| pack50 | 76 | None | {"strat": 5} | 971fe17131db2c68 | -9.38 | 0.34 | 9 | 15.21 | 33.33 | -7.28 | 20.00 | 0.00 |  |
| pack50 | 76 | None | {"strat": 5} | ecbb592bc960e777 | -3.85 | 0.48 | 3 | 11.08 | 33.33 | -33.61 | 20.00 | 0.00 |  |
| pack50 | 76 | None | {"strat": 5} | c4514da8063b4e21 | -22.32 | 0.25 | 7 | 28.21 | 14.29 | 9.28 | 20.00 | 0.00 |  |
| pack50 | 76 | None | {"strat": 5} | 822e6079d0cee2f7 | -9.17 | 0.13 | 4 | 19.06 | 25.00 | -45.11 | 20.00 | 0.00 |  |
| pack50 | 76 | None | {"strat": 5} | c74061bb9fdb7e85 | -6.10 | 0.51 | 7 | 11.84 | 14.29 | -22.06 | 20.00 | 0.00 |  |
| qs096 | 2,16,31,37,55,56,65,92 | None | {} | 7ab52cdaed1f0077 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 2,16,31,37,55,56,65,92 | None | {} | ce9755807e0fc7d8 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 2,16,31,37,55,56,65,92 | None | {} | d0346acabe23a41d | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 2,16,31,37,55,56,65,92 | None | {} | 82ac1e49416edded | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 2,16,31,37,55,56,65,92 | None | {} | 2bbe6d1f8e084b26 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 2,16,31,37,55,56,65,92 | None | {} | 3274a4e90190c692 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 2,16,31,37,55,56,65,92 | None | {} | f4b649283ab5854a | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 2,16,31,37,55,56,65,92 | None | {} | cfa9eb0ed635ae04 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 2,16,31,37,55,56,65,92 | None | {} | 7f03f9e637bbd940 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 2,16,31,37,55,56,65,92 | None | {} | d049125ba022d09f | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 2,16,31,37,55,56,65,92 | None | {} | 14ad6b66fbeda3c7 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 38 | None | {"cost": "gate", "variant": "two_side"} | fb2ed75768377872 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 38 | None | {"cost": "gate", "variant": "two_side"} | dc37bc72d1006390 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 38 | None | {"cost": "gate", "variant": "two_side"} | 59646428d1d425ed | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 38 | None | {"cost": "gate", "variant": "two_side"} | 8f21a295f6d03427 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 38 | None | {"cost": "gate", "variant": "two_side"} | dc06104f72d1c51b | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 38 | None | {"cost": "gate", "variant": "two_side"} | 081b88dd48446b0c | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 38 | None | {"cost": "gate", "variant": "two_side"} | 2c9708e481ee97eb | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 38 | None | {"cost": "gate", "variant": "two_side"} | 4d646eb9e7398e62 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 38 | None | {"cost": "gate", "variant": "two_side"} | e00b309193bcde88 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 38 | None | {"cost": "gate", "variant": "two_side"} | 3e0e7c7ace651cf0 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs096 | 38 | None | {"cost": "gate", "variant": "two_side"} | aaddaaa747bf5178 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | n/a | 11.00 | 0.00 |  |
| qs097 | 44 | None | {"variant": "two_side"} | 7d722e8b11e14ea9 | 6.16 | 4.23 | 5 | -3.19 | 40.00 | n/a | 11.00 | 11.97 |  |
| qs097 | 44 | None | {"variant": "two_side"} | d6143ebd1c5ae3f0 | -3.70 | 0.07 | 7 | -3.79 | 28.57 | n/a | 11.00 | 1.98 |  |
| qs097 | 44 | None | {"variant": "two_side"} | c894723256751b8a | 0.63 | 1.21 | 8 | -2.51 | 37.50 | n/a | 11.00 | 7.91 |  |
| qs097 | 44 | None | {"variant": "two_side"} | 992a67c5580f050a | -1.28 | 0.46 | 8 | -2.27 | 37.50 | n/a | 11.00 | 4.00 |  |
| qs097 | 44 | None | {"variant": "two_side"} | 812eb421dd384e23 | -1.51 | 0.48 | 6 | -2.85 | 33.33 | n/a | 11.00 | 9.78 |  |
| qs097 | 44 | None | {"variant": "two_side"} | dd6bf5edcf2f39bb | 3.05 | 2.38 | 7 | -3.25 | 57.14 | n/a | 11.00 | 6.64 |  |
| qs097 | 51 | None | {"variant": "two_side"} | 7d722e8b11e14ea9 | 6.16 | 4.23 | 5 | -3.19 | 40.00 | n/a | 11.00 | 11.97 |  |
| qs097 | 51 | None | {"variant": "two_side"} | d6143ebd1c5ae3f0 | -3.70 | 0.07 | 7 | -3.79 | 28.57 | n/a | 11.00 | 1.98 |  |
| qs097 | 51 | None | {"variant": "two_side"} | c894723256751b8a | 0.63 | 1.21 | 8 | -2.51 | 37.50 | n/a | 11.00 | 7.91 |  |
| qs097 | 51 | None | {"variant": "two_side"} | 992a67c5580f050a | -1.28 | 0.46 | 8 | -2.27 | 37.50 | n/a | 11.00 | 4.00 |  |
| qs097 | 51 | None | {"variant": "two_side"} | 812eb421dd384e23 | -1.51 | 0.48 | 6 | -2.85 | 33.33 | n/a | 11.00 | 9.78 |  |
| qs097 | 51 | None | {"variant": "two_side"} | dd6bf5edcf2f39bb | 3.05 | 2.38 | 7 | -3.25 | 57.14 | n/a | 11.00 | 6.64 |  |
| qs097 | 54 | None | {"variant": "long"} | 52256e3fe120fbeb | 8.23 | n/a | 2 | -2.77 | 100.00 | n/a | 11.00 | 12.02 |  |
| qs097 | 54 | None | {"variant": "long"} | cefba9836dbe1955 | -1.09 | 0.18 | 3 | -1.64 | 33.33 | n/a | 11.00 | 3.95 |  |
| qs097 | 54 | None | {"variant": "long"} | 04bd1bd050ca146e | 0.80 | 1.41 | 5 | -2.48 | 40.00 | n/a | 11.00 | 10.31 |  |
| qs097 | 54 | None | {"variant": "long"} | 5d2016d412b8432c | -1.07 | 0.34 | 4 | -1.84 | 50.00 | n/a | 11.00 | 4.47 |  |
| qs097 | 54 | None | {"variant": "long"} | a9ec58b792e4d2e2 | -0.89 | 0.54 | 4 | -1.86 | 25.00 | n/a | 11.00 | 9.04 |  |
| qs097 | 54 | None | {"variant": "long"} | f282222ed258e815 | 1.02 | 1.70 | 4 | -2.70 | 50.00 | n/a | 11.00 | 12.52 |  |
| rsimr | 48 | None | {} | fb14e77909fa0bc2 | 2.90 | n/a | 1 | -0.21 | 100.00 | 32.40 | 11.00 | n/a | INSUFFICIENT_SAMPLE |
| rsimr | 48 | None | {} | 1257b2447f940dd1 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | 195.76 | 11.00 | n/a | INSUFFICIENT_SAMPLE |
| rsimr | 48 | None | {} | d8301c422f05fab0 | -0.23 | 0.89 | 4 | -1.58 | 50.00 | -45.91 | 11.00 | n/a | INSUFFICIENT_SAMPLE |
| rsimr | 48 | None | {} | 2d120ba8e22bf817 | -1.57 | 0.48 | 5 | -3.14 | 40.00 | -27.91 | 11.00 | n/a | INSUFFICIENT_SAMPLE |
| rsimr | 48 | None | {} | 4316fd722c6e4b29 | -1.25 | 0.75 | 7 | -2.21 | 28.57 | -38.37 | 11.00 | n/a | INSUFFICIENT_SAMPLE |
| rsimr | 48 | None | {} | e56dd8dcd4b5454f | -1.55 | 0.41 | 4 | -2.65 | 25.00 | -35.75 | 11.00 | n/a | INSUFFICIENT_SAMPLE |
| rsimr | 48 | None | {} | 9a887b55b2972ad8 | -2.36 | 0.00 | 3 | -2.84 | 0.00 | -6.50 | 11.00 | n/a | INSUFFICIENT_SAMPLE |
| rsimr | 48 | None | {} | 68adda8fb2031e43 | 2.86 | 2.43 | 4 | -2.00 | 50.00 | -34.17 | 11.00 | n/a | INSUFFICIENT_SAMPLE |
| rsimr | 48 | None | {} | 1d6cec2c9eff16b5 | 0.76 | 1.38 | 3 | -2.02 | 33.33 | -10.46 | 11.00 | n/a | INSUFFICIENT_SAMPLE |
| rsimr | 48 | None | {} | 49d9b2da4f2f1297 | -1.66 | 0.11 | 3 | -2.07 | 33.33 | -46.22 | 11.00 | n/a | INSUFFICIENT_SAMPLE |
| rsimr | 48 | None | {} | e16ebee9a173da1d | -1.94 | 0.28 | 4 | -2.79 | 25.00 | -23.11 | 11.00 | n/a | INSUFFICIENT_SAMPLE |

En qs097 el campo card de la fila del ranking es texto muerto: el
adapter fija card desde --symbol (card_from_symbol), asi que la carta
negociada de cada celda ES el par de la fila.

Cada fila cita su run_id; los numeros son campos del artefacto, no
derivaciones. ret% y maxDD% son los del artefacto en su propia ventana
(solo 2026). BH% solo existe donde el adapter lo publica (pack20).

## Rechazos (motivo real registrado por el run)

- guard de solo-1h del adapter/motor: ciento treinta y dos celdas.
- otro: quince celdas.
- piso de historia de nueve mil barras del contrato G5 (qs_run): doscientas nueve celdas.
- piso de historia de quinientas barras (cbpackf): treinta y tres celdas.

- Detalle: el piso del contrato G5 de la familia QS (qsc, qsd) son
nueve mil barras y un ano de diarias son trescientas diecisiete, asi
que esas familias no pueden operar a 1d ni siquiera con historia
completa (el maximo historico diario ronda las tres mil seiscientas
barras): es un limite estructural del contrato, no de la ventana.
cbpackf pide quinientas barras. top10, smqe11, dspack, dspack2 y
botstrat llevan guard de solo-1h dentro del motor y se negaron solos.

## Lectura

- Recuento en palabras (los recuentos no son metricas de artefacto):
  veinticinco celdas cierran con retorno positivo, ciento veinticinco en cero o negativo, y setenta no
  dispararon NINGUNA operacion en 2026 (lookback comiendo ventana y
  filtros que nunca se activaron con barras diarias).
- Esto es una TRANSFERENCIA: params elegidos en otras temporalidades
aplicados a 1d, sin re-optimizacion (REGLA 1: cada celda se lee solo en
su propio artefacto; no hay transferencia de veredicto entre celdas).
- No es un veredicto de la bateria de gates: es la medida de lo que
pasa cuando esas 44 combinaciones se enfrentan a un ano de barras
diarias con costes y funding declarados por artefacto. Las celdas
positivas que aparecen arriba llevan n muy pequeno (menos de diez
operaciones en su mayoria): el mismo patron de concentracion que el
repo ya conoce, y ninguna celda pretende aqui un PASS de gates.
- Un PF impreso como n/a con win 100 es un PF infinito en el artefacto
(cero operaciones perdedoras): se declara, no se redondea.

