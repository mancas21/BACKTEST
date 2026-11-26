# Pre-registration — Non-Trend 50-Strategy Suite (#51–100)

Date: 2026-11-26. Written BEFORE the first artifact of this campaign exists.
The user chose the **full fifty rows**.

## Universos (declarados, no inferidos)

* **U** = todos los perps USDT-M con fichero 1h en `data/binance_klines_1h`
  excluyendo NVDAUSDT, SOLUSDC, SPCXUSDT, SPXUSDT y ficheros `*_tail_*`.
  El adjunto dice "17 símbolos"; hoy hay **22** en el repo. Se usan los 22 y
  se declara la diferencia: no se recorta el universo a ciegas para encajar
  una cifra antigua.
* **T** = los siete símbolos con CSV 5m taker-buy: BTC, ETH, HYPE, JUP, SOL,
  SUI, XRP.
* **F** = ocho perps con funding real y 1h: BTC, ETH, SOL, XRP, SUI, ARB,
  JUP, HYPE (el mismo octeto del libro `xsml`). El adjunto dice "8 con
  funding"; el repo tiene más, así que se fija este octeto por escrito.
* Todas las filas se correlacionan DENTRO del artefacto con el control #51
  calculado sobre el MISMO universo y ventana de la fila (así el número está
  medido, no ensamblado por el lector). Para las filas T/F el control se
  calcula sobre T/F; se declara que no es el control U del adjunto.

## Execution (común a las 50 filas)

* Señal y rank en el cierre de barra; rebalance y fills en el **open
  siguiente**. Libro dollar-neutral, igual peso por pierna, gross 1.0
  (0.5 largo / 0.5 corto) salvo las filas que declaran sizing propio.
* Costes repo 11 bps RT por turnover (5 fee + 0.5 slip por lado); 14 y 22 bps
  como sensibilidad dentro del artefacto. Funding real en cada liquidación
  sobre el nocional abierto (las filas T no lo cobran: su universo no incluye
  funding, limitación declarada).
* Un artefacto por fila, con `symbol` pseudo (`U_1H`, `T_5M`, `F_1H`) y todos
  los CSV del universo hashados como inputs. `cut_ts` por defecto.

## Las 50 filas, fijadas antes de correr

* **51–60** (U, 1h): MP-18 control (ROC168 con gate ROC336>0, top-2/bottom-2,
  rebalance 336); libro ancho top-3/bottom-3; return 168→24; ROC168/vol;
  residuo vs beta BTC; media de ranks 72/168/336; pesos 1/vol; cuatro
  sleeves desfasadas 84 barras; banda de retención top-4/bottom-4; gate
  direccional por ROC336.
* **61–68** (U, 1h): overlays sobre #51 — vol target 25%, freno de drawdown,
  régimen de vol de BTC, gate de dispersión, beta-neutral, stop por pierna,
  crash skip y exclusión de las tres menos líquidas.
* **69–76** (T, 5m): imbalance de taker, diferencias 7d−30d, z de flujo menos
  z de retorno, shock de volumen, share de barras con imbalance alto, suma
  7d normalizada, MP-18 con filtro de flujo y #69 con filtro de funding.
* **77–82** (F, 1h + funding): funding 7d como crowding, cambio de funding,
  ROC168 menos funding acumulado, MP-18 con filtro de percentil de funding,
  z-score de funding 8h, y cruce de signo de funding 7d (event-driven).
* **83–92** (U, 1h): vol realizada, lottery, vol del residuo, skewness, beta,
  cercanía al máximo de 720 barras, Amihud, volumen relativo, momentum dentro
  del subconjunto de baja correlación con BTC y share de días alcistas.
* **93–100** (composites): **solo se ejecutan si sus sleeves han pasado los
  gates por sí solas**. Si ninguna pasa, se declaran NO DATA sin número;
  mezclar sleeves fallidas no crea edge (regla del propio adjunto).

## Addendum, 2026-11-26 (antes de la primera corrida de mercado)

Los overlays del bloque B se implementan como **escala de exposición
declarada**, no como máquinas de estado literales: vol target 25% y freno de
drawdown se calculan sobre la curva del libro dentro del simulation; el gate
de vol de BTC y el gate de dispersión son series de escala 0.5/0 calculadas
con los datos servidos. Las filas **65 (beta-neutral exacto), 66 (stop por
pierna con reentrada) y 68 (exclusión por liquidez de 30 días)** NO están
implementadas con fidelidad suficiente: se declaran **NO DATA** y no se les
asigna ningún número, en lugar de publicar una cifra que no corresponde a
la regla del adjunto. Las compuestas siguen supeditadas a que sus sleeves
pasen gates.

## Gates y múltiples pruebas

Gate por fila: al menos 100 trades, 70% de folds rentables, 60% de meses en
verde, límite inferior del bootstrap de expectancy > 0, DD P95 < 35%, PF >
1.2 y net > 0. Se mide DSR con **N = 50** (pool declarado con la suite 1 y
corridas anteriores; no se inventa un N menor). Todo se calcula dentro del
artefacto. La correlación con el control #51 se reporta como medida
in-artifact; una fila que solo replica al control no aporta.

## Auditoría y publicación

`code/_nontrend50_audit.py` debe pasar ANTES de cualquier número de mercado:
known answers de rank largo/corto, neutralidad dollar, causality, signo de
funding, identidad contable y both-direction checks. Después: `pverify`
bit-for-bit, informe con `guard --strict` exit 0 y cada cifra junto a su
`run_id`. Ninguna fila se juzga por la suerte de otra (REGLA 1).
