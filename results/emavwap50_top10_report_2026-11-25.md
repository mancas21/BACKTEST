# Las 10 mejores (menos malas) filas del EMA×VWAP Suite

Date: 2026-11-25. Esta selección usa la regla fijada en `results/emavwap50_top10_criteria.md` antes de ordenar nada. Es una **selección post-hoc dentro de una familia KILLED**: ninguna fila pasó el gate y ninguna de estas diez es evidencia de alpha.

## Criterio aplicado

Solo filas con artefacto, al menos treinta operaciones y PF finito; se ordena por PF ex-cost descendente, con net %, PF de la mitad test y límite inferior del bootstrap como desempates. La columna ZERO se muestra pero no decide: es un control sin costes que nadie puede operar. Las filas sin datos y las de muestra insuficiente no entran en el ranking.

## Las diez elegidas

| # | Fila | TF | Net % | PF | Trades | ZERO % | Test PF | Boot LB | run_id |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 10 | 1h | -32.05 | 0.918 | 815 | 67.84 | 0.884 | -12.965 | `a7bc50e86524c36c` |
| 2 | 8 | 15m | -39.00 | 0.910 | 1612 | 214.90 | 0.786 | -7.131 | `9a3a743c9df89999` |
| 3 | 15 | 15m | -96.73 | 0.820 | 3757 | 65.28 | 0.626 | -4.788 | `61b483ec285ed7d7` |
| 4 | 42 | 5m | -100.00 | 0.739 | 14626 | 782.30 | 0.693 | -1.115 | `502cfdf5f700e415` |
| 5 | 7 | 15m | -74.37 | 0.728 | 1229 | -9.01 | 0.748 | -11.113 | `65436d450ad2a5aa` |
| 6 | 23 | 1h | -90.82 | 0.691 | 1639 | -45.41 | 0.862 | -8.871 | `a72a9414e3e9f771` |
| 7 | 21 | 15m | -98.56 | 0.615 | 3778 | -52.06 | 0.549 | -3.676 | `6f3ffcb2e101ce47` |
| 8 | 14 | 15m | -99.84 | 0.598 | 6727 | 44.90 | 0.528 | -1.867 | `380c732ccc45420c` |
| 9 | 6 | 15m | -99.95 | 0.579 | 6840 | -42.44 | 0.564 | -2.006 | `5e8dad13b9025034` |
| 10 | 20 | 15m | -99.98 | 0.560 | 7635 | -43.97 | 0.543 | -1.855 | `e406ac71686b5ee1` |

## Cómo leer esta lista

El orden es puramente relativo: el PF de la mejor fila sigue muy por debajo del suelo de 1.2, su red es negativa y su bootstrap no confirma nada. Las celdas con ZERO positivo muestran que el coste explica parte del desastre, pero eso no convierte a la fila en operable; las de ZERO negativo pierden incluso sin costes.

Elegir diez entre todas las elegibles después de ver los resultados es una forma de multiplicidad: el ranking está sesgado hacia arriba por construcción. No se le aplica un descuento arbitrario; simplemente no se usa como evidencia ni para reabrir un veredicto.

Las dos últimas filas de la tabla empatan en las cuatro claves de orden; el desempate lo decidió el orden en que aparecen en la matriz, no una medida nueva. Intercambiarlas no cambiaría ninguna conclusión.

## Provenance

- Criterio: `results/emavwap50_top10_criteria.md` (escrito antes de calcular el orden).
- Fuente: `results/emavwap50_report_2026-11-25.md` y sus artefactos, todos verificados bit a bit.
- Selección calculada: `results/emavwap50_top10_selection.json`.
- Ningún número nuevo: cada línea cita el `run_id` del artefacto que contiene la cifra.

