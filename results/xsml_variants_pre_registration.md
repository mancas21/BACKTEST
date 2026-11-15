# Pre-registración — `xsml` Variantes V2..V5 (2026-11-11)

**Estado:** PRE-REGISTRADO, NINGÚN RESULTADO TODAVÍA. Las cuatro variantes se
declaran juntas, se corren todas y se reportan todas (ganadoras y perdedoras).
**Libro base:** `results/xsml_pre_registration.md` (V1, ya medido y KILLED:
PF ex-cost 0.8830 OOS, control sin costes −7.38 %).

## Por qué abrir variantes (el diagnóstico, con números de V1)

Tres hechos medidos en el artefacto de V1 (`a2fc128ff0f42f5d`):

1. **El reward:risk del libro es 1:1.** Stop y objetivo están ambos a 2×ATR14,
   así que un acierto paga lo mismo que un fallo. Con win rate 49.5 % el libro
   está **por debajo del equilibrio por construcción**, y ningún forecast con
   correlación 0.1484 puede levantarlo por encima del ~52 % que exigen los
   costes de turnover (22 bps RT por rotación).
2. **La etiqueta no es lo que el libro realiza.** El modelo predice el retorno
   a 24 barras; el libro realiza un resultado con stop (2×ATR) y objetivo. El
   stop trunca por la izquierda exactamente el outcome que la etiqueta medía.
3. **El drag de costes es proporcional a los giros.** 186 rebalances × 22 bps RT
   = 1684.67 USDT de fees sobre 10.000 de equity (17 % del libro), y el funding
   real fue solo 50.33 USDT: el coste que mata este libro es el turnover, no el
   funding.

Cada variante ataca uno de esos tres hechos. **No se declara ninguna búsqueda de
hiperparámetros**: los modelos mantienen los hiperparámetros fijos declarados
en el pre-registro de V1, y cada variante es UN libro nuevo con su propio
`run_id`, sus propios artefactos y su propio veredicto.

---

## V2 — "la etiqueta es el payoff que el libro realiza"

**Hipótesis (H2):** el modelo predice bien la etiqueta equivocada. Si se le
entrena para predecir **el resultado que el libro realmente realiza** (el
payoff con las reglas de stop/objetivo del propio libro), el rank que produce
vale más que el rank que produce hoy.

- **Etiqueta:** payoff realizado desde la barra de señal, con las MISMAS reglas
  de ejecución del libro (entrada al open siguiente, stop 2×ATR, objetivo
  2×ATR, stop-first, gap-through al open): `+1R` si toca el objetivo, `−1R` si
  toca el stop, y el retorno a cierre del horizonte si no toca ninguno (en
  unidades R, con el stop como unidad).
- **Features:** las 10 declaradas, sin cambios.
- **Modelo:** `HistGradientBoostingRegressor` con los mismos hiperparámetros
  (max_iter 200, lr 0.05, depth 3, min_samples_leaf 20, l2 1.0, seed 42).
- **Split:** DEV hasta 2026-04-30, OOS desde 2026-05-01, embargo 24 barras.
- **Todo lo demás:** igual que V1.

## V3 — "menos giros, más señal por giro"

**Hipótesis (H3):** el edge por operación es real pero se paga demasiado a
cada giro. Con horizonte y rebalance a 72 barras (3 días) el número de giros se
divide por ~3 y el mismo edge por operación se cobra tres veces menos.

- **Etiqueta:** retorno a 72 barras, demeaned cross-sectionalmente.
- **Rebalance:** cada 72 barras (cada 3 días a las 00:00 UTC).
- **Stop/objetivo:** 2×ATR14 (sin cambios) — V3 cambia SOLO la frecuencia.
- **Features, modelo, split, ejecución:** iguales a V1.

## V4 — "reward:risk asimétrico (3:1)"

**Hipótesis (H4):** con 1:1 el libro necesita ~52 % de aciertos para cubrir
costes, y un forecast de correlación 0.15 no llega. Con objetivo 3×ATR y stop
1×ATR el libro necesita ~26 % de aciertos: un libro de tendencia real (gana
poco y pierde poco, y a veces gana mucho) puede pagar con una tasa de acierto
modesta.

- **Etiqueta:** payoff realizado con objetivo 3×ATR y stop 1×ATR (mismas reglas
  de ejecución), en unidades R con el stop como unidad.
- **Ejecución:** stop 1×ATR14, objetivo 3×ATR14.
- **Features, modelo, split:** iguales a V1.

## V5 — "un solo lado" (control de falsificación de H0)

**Hipótesis (H0 que V5 falsifica):** el poder predictivo del rank es real pero
asimétrico, y lo que se mide en el libro neutral es el lado equivocado. V5 corre
el MISMO modelo de V1 (mismas predicciones, mismo input, por tanto `run_id`
distinto solo por los params) en dos variantes de un lado:

- **V5-long:** solo las 3 predicciones más altas, sin pierna corta.
- **V5-short:** solo las 3 predicciones más bajas, sin pierna larga.

Si V5-long y V5-short pierden ambos, el problema no es "el lado equivocado":
es que el rank no tiene contenido operable. Si uno de los dos gana, el edge es
de un solo lado y se declara como tal (con su propia hipótesis y su propio
veredicto, sin reciclar el de V1).

---

## Gates (idénticos para las cuatro variantes, y para las dos celdas de V5)

Se aplican los mismos que en el pre-registro de V1, sin relajar ninguno:

1. `n ≥ 100` trades cerrados.
2. `PF ex-cost > 1.2`.
3. OOS net > 0.
4. `commission/gross < 30 %`.
5. Concentración: sin los cinco mejores trades el resultado sigue positivo.
6. Tercios: verde en ≥ 2 de 3.
7. Win rate ≥ 75 % ⇒ ≥ 5 pp sobre el win rate de equilibrio.
8. Control a coste cero DENTRO del artefacto (el drag se mide, no se deriva).
9. **KILL automático:** OOS PF < 1, o n < 100, o concentración top-5 > 100 % del
   PnL, o neto OOS < 0.

## Qué NO se hace

- No se busca la variante que "sale bien": las cuatro se reportan, y si las
  cuatro mueren, el veredicto es que el libro base era la mejor de las cuatro y
  se cierra la línea (sin una quinta).
- No se re-ajusta el modelo en ninguna variante (mismos hiperparámetros fijos).
- No se toca `code/xrp_neutral_engine.py` ni ningún engine hash-locked.
- No se comparan estas variantes con ningún libro muerto del repo para
  justificar nada (REGLA 1: cada libro se juzga por sus propios artefactos).

## Qué se reporta

Un informe por libro (`results/xsml_variants_report.md`), con la tabla de las
cuatro variantes (y las dos celdas de V5), **gate por gate**, con los `run_id`
y las rutas de artefacto, y `guard --strict` obligatorio. Si alguna variante
pasa, su veredicto se escribe en `STATUS.md` con su propio `run_id`; si ninguna
pasa, se escribe el cierre de la línea.

## Trazabilidad

- `code/xsml_model.py --variant <v2|v3|v4>` → `data/xsml_preds_<variant>.csv`
  (cada fichero de predicciones es INPUT del artefacto: su sha entra en el
  `run_id`).
- `code/xsml_engine.py` con `stop_mult`, `target_mult`, `long_only`,
  `short_only`, `rebalance_bars` → artefactos `vrun.py` (adapter `xsml`).
- Este spec: `results/xsml_variants_pre_registration.md`.
