# Pre-registración — `prompts100`: re-screen de los cien prompts con el harness del repo

**Estado:** PRE-REGISTRADO, NINGÚN RESULTADO TODAVÍA.
**Fecha:** 2026-11-12 · **Adapter previsto:** `prompts100`
**Motivo:** el pack original (`Downloads/backtest100_*`) **ordenó los cien
prompts por su propio OOS Profit Factor** y publicó un "Top 5" con esos
números. Elegir por una métrica medida en el tramo out-of-sample convierte ese
tramo en un tramo de *selección*: deja de ser una estimación fuera de muestra
y pasa a ser el criterio de entrada. Este re-screen repite la criba **sin
contaminar**: la selección se hace SOLO sobre un tramo que el veredicto nunca
mira.

## 1. Qué se re-screen y qué no

El pack trae tres familias con tres formas distintas, y se miden las tres:

| familia | ids | forma | libro |
|---|---|---|---|
| A — un solo símbolo | 1–80 | función de señal `f(j, ctx) -> {side, stop_px, tp_px, max_hold}` | una pierna |
| B — par o cesta | 81–90 | función que calcula sus propias series de lado y stop | dos piernas (o cesta) dollar-neutral |
| C — funding | 91–100 | función que calcula sus propias series de lado y stop | una pierna, con funding |

Cobertura de datos: **los ochenta ids de la familia A tienen klines en este
repo** (BTC/ETH/SOL/HYPE/SUI/JUP en 1h, 15m y 5m). Las familias B y C usan
las mismas series más el fichero de funding.

**No se re-screenea la criba del pack** (sus ids, su orden, su "Top 5"): se
re-screenean los **cien prompts**, todos, y el ranking es **nuestro**.

## 2. Origen del código (portado, no reescrito)

El código del pack vive en `Downloads/`, que **no es durable** (la lección del
SAX v3: un engine borrado se llevó 49 artefactos). Por eso el código se
**copia verbatim** a `code/prompts100/` con un manifiesto de sha256, y todo lo
que se ejecuta en el repo se ejecuta contra esa copia.

- `backtest100_strategies.py` — las 100 funciones de señal (familias A).
- `backtest100_engine.py` — el motor del pack (referencia, NO se ejecuta en el
  repo salvo en la prueba de paridad).
- `backtest100_pairs_engine.py` — los pares y cestas (familia B).
- `backtest100_funding_strategies.py` — los libros de funding (familia C).

## 3. Convenciones de ejecución (las del repo, declaradas)

La señal del pack es **verbatim**; la ejecución es la del repo. Se declara
explícitamente en qué se diferencia del motor del pack, porque la diferencia
es de primer orden:

| regla | motor del pack | **este repo** |
|---|---|---|
| entrada | al open siguiente | al open siguiente (igual) |
| salida por señal | al open siguiente | al open siguiente (igual) |
| señal de lado contrario | **revierte** la posición al siguiente open | **revierte** la posición al siguiente open (igual) |
| stop primero en empates | sí | sí (igual) |
| stop atravesado por hueco | rellena **al open** | rellena **al open** (igual) |
| hueco de ENTRADA que ya atraviesa el stop | **se descarta el trade** ("setup inválido") | **se rellena al open** (el repo no descarta operaciones: un hueco malo es un resultado malo, no un trade que no existe) |
| costes | la constante del pack es `0.000055` = **0.55 bps por lado** (1.1 bps RT efectivos), pese a que su comentario y su documentación dicen "5.5 bps" (11 bps RT). Medido: el factor es diez | **11 bps RT** (5 bps de comisión + 0.5 bps de slip por lado), tal como manda el repo |
| funding | **no se cobra** (salvo familia C) | **se cobra en los settlements reales**, en las dos piernas |
| tamaño | 1 % del equity arriesgado en el stop, tope 20x | 1 % del equity arriesgado en el stop, tope 20x (igual) |
| posiciones | una a la vez | una a la vez (igual) |

Las tres diferencias marcadas (hueco de entrada, costes, funding) son
**deliberadas**: son las reglas del repo, y son más honestas (no se descartan
operaciones malas) o más severas (costes reales y funding). El informe publica
la **atribución** de la diferencia: cuánto de la variación entre el número del
pack y el nuestro viene de cada regla.

> **CORRECCIÓN DEL SPEC (2026-11-12, antes de la primera corrida de mercado).**
> La primera redacción de esta tabla decía que el pack cobraba "5.5 bps por
> lado en el precio + 5.5 bps de comisión = 22 bps RT efectivos". **Era
> falso**: la constante del pack es `FEE_PER_SIDE = 0.000055`, que es
> **0.55 bps** (1 bp = 1e-4), no 5.5. El coste real del pack es por tanto
> **1.1 bps round trip**, diez veces más barato que el estándar del repo y
> cien veces más barato que el ida y vuelta real de un taker en Binance.
> El error lo destapó la prueba de paridad (los fills del pack salen un
> factor diez más baratos que los del repo) y se corrigió ANTES de correr
> nada: este spec estaba congelado pero todavía no había servido para ningún
> resultado de mercado. El resto del diseño (tramos, gates, control de
> multiplicidad) no cambia.

## 4. Tramos (la parte que quita la contaminación)

Ventana de mercado común para las cien estrategias, para que la comparación sea
entre estrategias sobre **el mismo régimen**:

- **DEV (selección)** — todo lo disponible hasta `2025-10-01` (UTC).
- **PURGA** — `2025-10-01` a `2025-10-31`: el libro **no opera** (ni señales,
  ni posiciones). Es la separación entre selección y veredicto.
- **OOS (veredicto)** — desde `2025-11-01` (UTC) hasta el final del store.

La **selección usa solo DEV**. El OOS no se mira hasta que la criba esté
cerrada, y se lee entero para las cien estrategias.

**Muestra mínima declarada:** una estrategia es MEDIBLE si tiene ≥ 30 trades en
DEV. Por debajo se reporta INSUFICIENTE MUESTRA y **no se estima nada**.

## 5. Gates

**Criba (sobre DEV), los mismos ocho del comando del contrato
(`bt.py one`):** `pf > 1.2`, `n >= 30`, `net > 0`, `thirds >= 2`,
`oos_pf` (no aplica en DEV), `conc <= 100 %`, `sig` (bootstrap CI del R medio
por trade, IC95 excluyendo cero) y `boot_ci > 0`.

**Veredicto (sobre OOS):** los mismos gates, con `n >= 100` (G1 completo),
`PF ex-cost > 1.2`, `net > 0`, `concentración` (los cinco mejores trades como
porcentaje del PnL total ≤ 100 % **y** el resultado sin ellos sigue positivo),
`tercios ≥ 2 de 3` verdes, `bootstrap CI por bloques excluyendo cero`, y
comparación con buy & hold (el exceso OOS se imprime; un libro que solo gana
porque el mercado no cayó no es alpha).

**Control del multiple testing (declarado antes de correr):** con cien
estrategias cribadas, la métrica OOS del ganador está sesgada al alza. Se
publica la **distribución completa de las cien métricas OOS** y una lectura
extra: un superviviente tiene que superar el percentil 95 de esa distribución
—es decir, distinguirse del propio ruido de la criba—. Si no lo supera, el
veredicto lo dice aunque las otras puertas sean verdes.

**KILL automático:** PF OOS < 1, o n OOS < 100, o concentración top-5 > 100 %
del PnL, o neto OOS < 0.

## 6. Cadena de prueba (la del repo, en orden)

1. **Paridad de señal** — las señales del port deben ser **idénticas** a las
   del motor del pack sobre datos reales (mismo conjunto de eventos: barra,
   lado, stop, objetivo). La paridad prueba la SEÑAL; no prueba nada de la
   ejecución que se le añade encima.
2. **Paridad de libro** — con las convenciones DEL PACK (22 bps, hueco de
   entrada descartado, sin funding), el port debe reproducir los números del
   pack. Si eso no cuadra, la diferencia posterior se atribuye a las reglas
   del repo y no a un error de port.
3. **Respuestas conocidas en AMBAS direcciones** — fill, PnL, stop-first, hueco
   a través del stop, hueco de entrada, signo del funding, coste en las dos
   piernas, invariante contable. (La lección de WAVE_1: tests solo del lado
   largo y un bug de comisión en el corto durante toda la campaña.)
4. **Invariante contable asertado DENTRO de cada artefacto**:
   el equity final menos el inicial tiene que igualar la suma de los PnL menos
   el funding pagado. Un ledger roto aborta en vez de dar un PF creíble.

## 7. Qué NO se hace

- **No se re-ajusta ningún prompt.** Los cien se ejecutan tal cual, con los
  hiperparámetros del pack. No hay grid, ni Optuna, ni selección por score.
- **No se usa el "Top 5" del pack como entrada.** Se criban los cien.
- **No se mira el OOS antes de cerrar la criba** sobre DEV.
- **No se toca ningún engine hash-locked** (`code/xrp_neutral_engine.py`,
  `code/cbpack_engine.py`, `code/scalp_wave_engine.py` y compañía).
- **No se comparan estrategias entre sí para decidir** (REGLA 1): cada libro se
  juzga por sus propios artefactos; la distribución de las cien métricas se
  publica como control de multiplicidad, no como comparación de mérito.

## 8. Trazabilidad

- Código del pack, copiado verbatim: `code/prompts100/` + manifiesto sha256.
- Motor del repo: `code/prompts100_engine.py` (familias A, B y C).
- Paridad: `code/_prompts100_parity.py`.
- Respuestas conocidas: `code/_prompts100_audit.py`.
- Adapter: `prompts100` en `code/vrun.py` (params: `id`, `segment`).
- Informe: `results/prompts100_rescreen_report.md` (guard `--strict`).
- Este spec: `results/prompts100_rescreen_pre_registration.md`.
