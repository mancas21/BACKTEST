# Criterio para elegir las 10 mejores filas del EMA×VWAP 50-Strategy Suite

Date: 2026-11-25. Written BEFORE computing the ranking.

## Qué se decide

Se ordenan las filas del suite `results/emavwap50_report_2026-11-25.md`
según una regla fija y se publican las diez primeras. Es una **selección
post-hoc sobre la misma muestra que mató a toda la familia**: no es un
veredicto nuevo, no es una resurrección y no es evidencia de alpha.

## Elegibilidad

Entran solo filas con artefacto propio, `n_trades >= 30` y `profit_factor`
finito. Quedan fuera:

* las filas NO DATA (sin CSV en su TF o sin dato externo), que no tienen
  número que ordenar;
* las filas NO VERDICT por muestra insuficiente, aunque tengan PF.

## Regla de orden (fija, sin ajustes)

1. **PF ex-cost descendente** (coste repo de 11 bps RT + funding real), que
   es la medida principal ya publicada.
2. Si hay empate, **net % descendente**.
3. Si sigue hay empate, **PF de la mitad test (70/30) descendente**.
4. Si sigue hay empate, **límite inferior del bootstrap descendente**.

Se toman las diez primeras de esa lista. La columna ZERO (control sin
costes) se muestra pero **no se usa para ordenar**: ordenar por ella sería
elegir sobre un régimen que nadie puede operar.

## Declaración obligatoria

* Ninguna de las filas elegibles pasó el gate pre-registrado (PF > 1.2,
  net > 0, test positivo, bootstrap > 0, concentración < 100%). Las diez
  elegidas son las **menos malas**, no las buenas.
* Elegir diez entre veintidós tras ver los resultados multiplica las
  pruebas: el ranking está sesgado hacia arriba por construcción. No se
  le aplica ningún descuento inventado; simplemente **no se presenta como
  evidencia**.
* Cada número del informe debe salir de un artefacto y citar su `run_id`;
  los conteos van en palabras; `guard --strict` debe devolver 0.
