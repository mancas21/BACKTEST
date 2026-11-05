# Registro de estrategias — generado, no editar

Fuente: barrido de `results/runs/` deduplicado por (adaptador, estrategia, par, tf).
Cada fila cita su artefacto (`results/runs/<run_id>.json`). Regenerar:

    python code/strategy_registry.py

Vistas: `by_symbol/<PAR>.md`, `by_tf/<TF>.md`, `by_family/<FAMILIA>.md`.

Columnas clave:
- `ret_declared_pct`: retorno del artefacto canonico (costos declarados del artefacto).
- `ret_zero_cost_pct`: control de costo cero medido dentro del artefacto cuando existe.
- `ret_repo_11bps_pct`: re-medicion a 11 bps RT (dspack completo; resto = su declarado).
- `fill_model`: taker_next_open (certificable en OHLC) vs maker_intrabar
  (NO certificable sin resolucion 1m / forward — leccion XRP 2026-10-31).
- `verdict`: veredicto del pack o de la fila; nunca confundir retorno con validacion.

Dimensiones: 37 pares, 8 timeframes, 21 familias,
1721 estrategias.
