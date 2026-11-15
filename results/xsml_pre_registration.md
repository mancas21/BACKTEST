# Pre-registración — `xsml`: libro cross-sectional con filtro ML (1h, perps, dollar-neutral)

**Fecha de escritura:** 2026-11-11 · **Estado:** PRE-REGISTRADO, NINGÚN RESULTADO TODAVÍA
**Adapter previsto:** `xsml` · **Familia de registro:** `ml_cross_sectional`
**Engine previsto:** `code/xsml_engine.py` · **Reglas de ejecución:** las del repo (next-open, stop-first, gap-through al open, 1% de riesgo)

Este documento se escribe **antes** de la primera corrida, y no se modifica después.
Si el libro muere, muere con este spec congelado. No hay segunda vuelta con otro
grid: un `n_trials` implícito sería exactamente el sobreajuste que este repo ya
ha matado en otras familias.

---

## 1. Tesis (mecanismo, no correlación)

**Los perps de Binance tienen un coste de financiación público, recurrente y
signed.** El precio del funding es lo que el mercado paga (o cobra) por mantener
una posición a través del settlement, y **su signo y magnitud difieren por
símbolo y por momento**. Eso crea dos efectos con mecanismo económico:

1. **Carry cross-sectional:** en un mismo instante, un símbolo con funding
   negativo paga por su posición larga y uno con funding positivo la cobra. Un
   libro que ordene símbolos por su estado de financiación y tome el lado que
   *recibe* está capturando un flujo que existe aunque el precio no se mueva.
2. **El coste de mantener el lado equivocado:** un libro cross-sectional que
   ignora el funding paga un spread de financiación que se come el edge bruto
   antes de cualquier gate.

**Hipótesis (H1):** el orden cross-sectional de un forecast de retorno relativo
—construido con momentum multi-timeframe, régimen de volatilidad, participación
y estado de financiación— **contiene más información que el propio retorno
pasado**, y esa diferencia es lo bastante grande para sobrevivir a 22 bps de
coste round-trip (11 por pierna) más el funding pagado en las dos piernas.

**Qué la distingue de los libros ya muertos (REGLA 1: esto es una hipótesis
nueva, no un re-run):** los libros cross-sectional previos del repo
(`xsf`/`xsb`/`xsc`) ordenaban por **factores fijos** (volatilidad realizada,
skew, autocorrelación) con ventanas fijas y **sin funding**. Aquí (a) el ranking
lo produce un modelo entrenado sobre features declaradas, (b) el funding entra
como feature y como coste, y (c) el universo es point-in-time.

**Hipótesis alternativa que el propio libro debe falsificar (H0):** el ranking
no tiene contenido y lo que se mide es la exposición beta del lado largo.

## 2. Universo y ventana (declarados, no ajustables)

Nombres = los que tienen **klines 1h Y fichero de funding** en el store:

    BTCUSDT  ETHUSDT  SOLUSDT  XRPUSDT  SUIUSDT  ARBUSDT  JUPUSDT  HYPEUSDT

**Point-in-time:** un nombre entra en la cross-section cuando tiene ambas
series; sale si deja de tenerlas. Cada fecha usa **solo** los nombres
disponibles ese día (y las features se normalizan cross-sectionalmente por
fecha, así que el cambio de composición no sesga la entrada).

**Inicio del estudio:** `2024-10-01` (cuando el 6º nombre, JUPUSDT, tiene klines
*y* funding). **Fin:** último bar 1h cerrado del store.

**Fin de DEV:** `2026-04-30` · **Inicio de OOS:** `2026-05-01` · **Embargo:** 24
baras (1 día) a cada lado del corte — el horizonte de la etiqueta es 24 barras,
así que sin embargo las muestras del borde se solapan con el test.

## 3. Etiqueta (target)

`y[i] = (close[i+24] / close[i] - 1)` **demeaned cross-sectionalmente por
fecha** (se resta la media de la fecha). El modelo predice **retorno relativo**,
no nivel: así el objetivo no premia el beta del mercado y H0 queda falsable.

## 4. Features (10, declaradas antes de correr)

| # | feature | definición | por qué |
|---|---|---|---|
| 1 | `mom_24` | retorno 24 barras 1h, demeaned por fecha | momentum corto |
| 2 | `mom_72` | retorno 72 barras, demeaned | momentum medio |
| 3 | `mom_1d` | (close/SMA20 en barras 1d comprimidas − 1), demeaned | tendencia diaria (multi-interval) |
| 4 | `vol_pct` | percentile del ATR14 en bps sobre 300 barras | régimen de volatilidad |
| 5 | `vol_ratio` | ATR14 bps / mediana ATR bps (300) | expansión de volatilidad |
| 6 | `chop` | CHOP(14) | trending vs ranging |
| 7 | `vol_z` | z robusto de log1p(volumen) sobre 101 barras | participación |
| 8 | `vwap_dist` | (close − VWAP_sesión)/σ_sesión | extensión dentro del día |
| 9 | `fund_last` | último settlement de funding ×1e4 bps | carry inmediato |
| 10 | `fund_avg3` | media de los 3 últimos settlements ×1e4 bps | carry persistente |

Todas **causales**: valor en la barra `i` depende solo de `≤ i`.
Feature #3 requiere barras 1d comprimidas (se calculan desde el mismo 1h).

## 5. Modelo (fijo, sin búsqueda)

`sklearn.ensemble.HistGradientBoostingRegressor`
`max_iter=200, learning_rate=0.05, max_depth=3, min_samples_leaf=20,
l2_regularization=1.0, random_state=42`
Se ajusta **una vez** con todo DEV (con purge/embargo en el borde) y predice
**todo** OOS. **No hay grid search, ni Optuna, ni selección de modelo por
performance**: el modelo se elige a priori y se reporta como salió.

## 6. Cartera

- Cada **24 barras** (1d), en la barra de rebalance: rank de la predicción
  (descendente). **Long top-3, short bottom-3**, dollar-neutral, peso igual por
  pierna (1/6 del equity bruto por posición, 50% long / 50% short).
- Si hay menos de 6 nombres disponibles en la fecha, esa fecha **no se opera**
  (se registra) — no se degrada el sizing.
- Scores no definibles (NaN por warmup) → el nombre no entra en el rank.

## 7. Ejecución (la del repo, no la de pybroker)

- Señal en la barra cerrada de rebalance → **entrada al open de la siguiente
  barra**.
- **Stop-first en empates**; un open que abre más allá del stop **rellena al
  open**; el rango de la barra de entrada **sí** se comprueba (el fill es al
  open de esa barra, su rango es posterior).
- Stop por pierna: 2×ATR14 bps, congelado en la barra de señal.
- Tamaño: 1% del equity arriesgado por pierna al stop; sin apalancamiento
  (tope 100% del equity por libro).
- Salida: stop, objetivo (2×ATR) o fin de datos (cierre forzado).
- Coste: **11 bps round-trip por pierna** (5 bps de comisión + 0.5 de slip por
  lado), cobrado en entrada y en salida, en las dos piernas.
- **Funding cobrado en los settlements reales**, en las dos piernas (es la
  lección del repo: un libro neutral que ignora funding no es neutral).

## 8. Gates (GATES v2) y qué significa PASS / KILL

**PASS exige TODO:**
1. `n ≥ 100` trades cerrados (G1).
2. `PF ex-cost > 1.2` (G2), y **OOS PF > 1.2** (G3) — el OOS manda.
3. `commission/gross < 30%` (G4).
4. Concentración: quitar los 5 mejores trades deja el resultado **positivo**
   (G5) — si el top-5 se lleva >100% del PnL, KILL.
5. Period split: **verde en ≥2 de 3** tercios (G6).
6. **Win rate ≥ 75% ⇒ debe estar ≥5pp por encima del win rate de equilibrio**
   (G11, el que más mató libros aquí).
7. Sin concentración en un solo símbolo: el PF por símbolo no puede ser el
   motor (se reporta; si el agregado vive de un símbolo, KILL).
8. Null: el resultado no puede distinguirse del ruido (null de entrada
   aleatoria / bootstrap CI).
9. **Funding y costes incluidos en todas las cifras.**

**KILL automático:** OOS PF < 1 (regla del repo), o n < 100, o concentración
top-5 > 100% del PnL, o net OOS < 0.

## 9. Lo que este libro NO hace (declarado)

- No se re-optimiza si muere. Un spec congelado que sale mal, sale mal.
- No se reportan números de pybroker: los artefactos los emite el harness del
  repo (`vrun.py`), con `run_id`, `verify` y `guard --strict`.
- No se compara con ningún libro muerto para justificar nada (REGLA 1).
- No se toca `code/xrp_neutral_engine.py` ni ningún engine hash-locked.

## 10. Riesgos declarados (antes de saber el resultado)

1. **Ventana corta:** 25 meses es poco para ML. El DEV tiene ~19 meses de
   observaciones cross-sectionales (millares) pero solo 7 de OOS efectivo.
2. **Competir con el pasivo:** un libro neutral no bate al buy&hold por
   construcción; su benchmark es el spread. Si el spread no cubre 22 bps +
   funding, el libro muere por costes, no por señal.
3. **El funding puede ser espurio:** en perps el funding medio de un símbolo
   tiende a premiar al lado que ya va ganando (sesgo del propio mercado). El
   libro debe pasar el control de que el edge no desaparece al neutralizar el
   lado del carry — si desaparece, H1 queda falsada y es un FAIL, no un "casi".
4. **Selección de la tesis:** el libro se elige porque tiene mecanismo y porque
   la literatura del repo apunta ahí; si muere, no se busca otra tesis hasta que
   una salga bien (eso es lo que `GATES_AND_RULES.md` prohíbe).

## 11. Trazabilidad

- Features: `code/xsml_features.py` (motor pybroker, venv `~/.venvs/pybroker`)
  → `data/xsml_features_1h.csv`
- Modelo + predicciones: `code/xsml_model.py` → `data/xsml_preds.csv`
- Backtest con ejecución del repo: `code/xsml_engine.py` → artefactos `vrun.py`
  (adapter `xsml`)
- Informe: `results/xsml_report.md` (guard OK strict obligatorio)
- Este spec: `results/xsml_pre_registration.md`
