# Pre-registración — `xsml`: ambigüedad del TURNOVER del spec congelado (2026-11-11)

**Estado:** PRE-REGISTRADO, NINGÚN RESULTADO DE LA LECTURA ALTERNATIVA TODAVÍA.
**Dispara:** un defecto de contabilidad del engine (signo del lado corto), no
una idea nueva. Al corregirlo, las cifras del libro base cambian y aparece
una ambigüedad en la spec congelada que hay que resolver ANTES de mirar el
resultado de la otra lectura.

## 1. El defecto que obliga a re-correr (no es una variante)

El engine `xsml` multiplicaba por `side` una cantidad que **ya era firmada**
(`qty = side * notional / fill`). Consecuencia: cada pierna corta se
contabilizaba como un espejo-largo, y su comisión se ACREDITABA en vez de
cobrarse. Lo detectó el invariante contable del repo:

    eq[-1] - INIT == sum(pnl) - funding_paid

que fallaba con un residuo de **1689.65 USDT** = exactamente cuatro comisiones
por cada uno de los 507 trades cortos. El artefacto `a2fc128ff0f42f5d` y su
informe (`results/xsml_report.md`) publicaron cifras de ese ledger roto: ese
informe queda **RETIRADO**.

Corrección (obligatoria, no es elección): una sola cantidad firmada en todo
el libro — `cash -= qty*fill + fee` al entrar, `cash += qty*fill - fee` al
salir, `equity = cash + qty*mark`, `funding -= qty*mark*rate`. El invariante
ahora se **aserta dentro del artefacto** y el residuo se publica
(`pnl_identity_resid`).

Suite de respuestas conocidas: `code/_xsml_engine_audit.py`, **29/29 PASS**,
con el lado corto cubierto en todas las reglas (fill, PnL, stop-first, gap,
funding, invariante). La lección de WAVE_1 —"tests solo del lado largo y un
bug de comisión en el corto durante toda la campaña"— queda cubierta.

## 2. La ambigüedad que hay que resolver

La spec congelada (`results/xsml_pre_registration.md`) dice:

- §6: "Cada **24 barras** (1d), en la barra de rebalance: rank de la
  predicción. **Long top-3, short bottom-3**, dollar-neutral, peso igual por
  pierna (1/6 del equity bruto por posición, 50% long / 50% short)."
- §7: "Salida: **stop, objetivo (2×ATR) o fin de datos** (cierre forzado)."

Ninguna de las dos frases dice si una pierna que **sigue seleccionada** se
cierra y se reabre, o si se queda con su posición original. Son dos libros
distintos y el coste de giro es de primer orden.

**Lectura A — giro COMPLETO (la que se implementa como principal).**
En cada rebalance se cierran las seis piernas y se abren las seis nuevas al
siguiente open. Lectura literal de §6 (la cartera ES top-3/bottom-3 en cada
barra de rebalance) y de §7 ("stop congelado en la barra de señal": el stop
de cada pierna se congela en la barra de señal de ESE rebalance). Es también
lo que decía el docstring del propio engine. Consecuencia: el libro rota
100 % de su nocional cada 24 barras → ~22 bps de equity por rebalance.

**Lectura B — se cierra solo lo que SALE del ranking.**
Una pierna que sigue seleccionada conserva su posición, su stop y su tamaño
(la spec "congelado en la barra de señal" se lee como la barra que la
abrió). Es la lectura que implementaba el código de la versión 1 del engine y
la más barata en giros. Consecuencia: el libro arrastra posiciones de
distintas vigencias y su peso puede apartarse del 1/6 declarado.

**Por qué se declara ahora y no se elige por el resultado:** la elección se
hizo al notar la ambigüedad, ANTES de correr la lectura B, y las dos
lecturas se reportan. La lectura A da peores cifras (más coste de giro), así
que no es una elección de la que salga bien.

## 3. Qué se corre (las DOS lecturas, declaradas por adelantado)

Los **cinco libros** de la campaña de variantes (`results/xsml_variants_pre_registration.md`,
V1 base + V2 + V3 + V4 + V5-long + V5-short) se corren en **las dos lecturas**
del turnover. Son 12 artefactos. Cada libro se juzga por SUS artefactos
(REGLA 1) y los gates son los mismos, sin relajar ninguno.

Un libro = una lectura del turnover + una variante del modelo. Ningún par de
lecturas se compara como "candidata" contra la otra: se reportan las dos, y
el veredicto dice si la conclusión es ROBUSTA a la ambigüedad (falla en las
dos) o depende de ella (falla en una).

## 4. Gates (idénticos, sin relajar)

1. `n ≥ 100` trades cerrados.
2. `PF ex-cost > 1.2`.
3. OOS net > 0.
4. `commission/gross < 30 %`.
5. Concentración: sin los cinco mejores trades el resultado sigue positivo.
6. Tercios: verde en ≥ 2 de 3.
7. Win rate ≥ 75 % ⇒ ≥ 5 pp sobre el win rate de equilibrio.
8. Control a coste cero DENTRO del artefacto (el drag se mide, no se deriva).
9. **KILL automático:** OOS PF < 1, o n < 100, o concentración top-5 > 100 %
   del PnL, o neto OOS < 0.

## 5. Qué NO se hace

- No se re-ajusta el modelo en ninguna variante (mismos hiperparámetros fijos).
- No se elige la lectura "que sale bien": se reportan las dos.
- No se toca ningún engine hash-locked (`code/xrp_neutral_engine.py` y compañía).
- No se citan libros muertos del repo para justificar nada (REGLA 1).

## 6. Trazabilidad

- `code/xsml_engine.py` con el param `turnover` (`full` | `keep`).
- `code/xsml_model.py --variant <v1|v2|v3|v4>` → `data/xsml_preds_<v>.csv`
  (INPUT del artefacto: su sha entra en el `run_id`).
- Artefactos: `vrun.py` (adapter `xsml`).
- Informe: `results/xsml_variants_report.md` (guard `--strict` obligatorio).
- Este spec: `results/xsml_turnover_pre_registration.md`.
