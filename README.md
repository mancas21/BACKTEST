# backtest-system — every strategy, measured, most of them dead
# backtest-system — cada estrategia, medida, la mayoría muerta

[English](#english) · [Español](#espa%C3%B1ol)

Artifact-backed backtesting of public trading strategies on Binance crypto
perpetuals. Nothing here is financial advice. Almost everything in this repo
is a **killed** strategy — that is the point: the lab shows its work.

Follow the lab on X: [@nftepml](https://x.com/nftepml) — "we ran the backtests
so you don't have to."

---

## Español

### Qué es este repo

Un laboratorio de backtesting personal, **con respaldo de artefactos**, para
estrategias públicas de trading en perpetuals de cripto (Binance USDⓈ-M,
1m–1d). La premisa: un número solo es un resultado si existe un artefacto de
corrida persistido que lo respalde y ese artefacto **se puede reproducir
bit a bit**. Todo lo demás es texto. El producto real del lab es, sobre todo,
**negativo**: de más de 1.700 estrategias medidas, la gran mayoría están
muertas, y el repo documenta por qué murieron con evidencia, no con opinión.

Estado medido el 2026-11-08: **5.342 artefactos** en `results/runs/`,
**1.721 estrategias** en el registro, **43 adaptadores** de motor en
`code/vrun.py`, **270** archivos Python en `code/`.

### REGLA 0 — ningún número sin artefacto

La regla fundacional (nació porque un agente reportó una vez un backtest
completo que nunca se corrió):

- Cada métrica publicada cita su `run_id` — un hash de los bytes del motor,
  los parámetros y los datos (con corte temporal: los apéndices de datos ya
  no invalidan artefactos antiguos).
- `verify` re-corrre el motor y **se niega** si el resultado no es idéntico
  bit a bit. Códigos: `0` OK · `2` REFUSED (manipulado / no reproducible) ·
  `3` STALE (los bytes de datos cambiaron; re-correr) · `4` ORPHANED (motor
  borrado del disco).
- `guard` rechaza cualquier reporte que contenga números que ningún artefacto
  respalda.
- Los escenarios sintéticos o ilustrativos se etiquetan como tales y nunca
  llevan `run_id`.

### REGLA 1 — una estrategia, un veredicto

Cada estrategia se juzga **solo** sobre sus propios artefactos. Que un
hermano parecido haya fallado antes no es evidencia de nada sobre esta: la
lista de muertos es historia, nunca un pre-gate.

### Estructura

| Ruta | Qué es |
|---|---|
| `code/` | Motores, harness (`vrun.py`), pipeline por etapas (`bt.py`), gates (`GATES v2`), auditorías, herramientas de datos |
| `data/` | La única fuente de mercado: klines de Binance (1m–1d, variantes taker), funding, aggTrades, equities de Alpaca; manifiestos de integridad (`FUNDING_MANIFEST.json`, `KLINES_MANIFEST.json`, …) |
| `results/runs/` | Los artefactos (no se distribuyen en la release pública; los `run_id` y el registro los referencian) |
| `results/registry/` | El universo: una fila por estrategia medida, con veredictos, régimen de costes y modelo de fills; vistas por símbolo/tf/familia |
| `results/REPORTS.md` | Índice de reportes con su estado `guard` — solo los OK son citables |
| `edge/` | El proyecto EDGE sellado (v4.1, veredicto terminal) + los master prompts (v5.2 indicadores → v6.1 puente a edge) |
| `recorder/` | Grabador de order-flow en vivo (bookTicker, depth, liquidaciones) para el track de datos grabados |
| `pine/` | Librería de scripts Pine (referencia y auditoría) |
| `content/` | `specs.md` (la receta exacta de cada estrategia publicada) y los hilos de X |
| `backups/`, `audit/` | Historiales y kits de auditoría independiente |

### El harness

```powershell
python code\vrun.py run    --strategy sax --tf 1h --symbol BTCUSDT   # correr → artefacto
python code\vrun.py render <run_id>    # los números salen SOLO del artefacto
python code\vrun.py verify <run_id>    # re-corrre; REFUSED si no es idéntico
python code\vrun.py guard  --report report.md --strict
python code\vrun.py matrix --strategy sax --workers 4
python code\vrun.py stats  <run_id>    # scorecard institucional
python code\bt.py one --strategy <s> --tf <tf> --symbol <sym>  # un artefacto, una batería, un veredicto
```

### Las puertas (gates)

- **Criba**: PF ex-costes > 1.2, n ≥ 30 trades, verde en ≥ 2/3 de años,
  estabilidad de vecindario, walk-forward/OOS. **OOS PF < 1 = KILL**, sin
  bucles de rescate.
- **Batería completa**: `GATES_AND_RULES.md` (v2, G1–G11): n ≥ 100 para
  veredicto completo, Ljung-Box de expectancia, folds de walk-forward,
  costes < 30%, breakeven de win-rate, calibración nula.
- **Costes**: 11 bps ida-y-vuelta direccionales (medidos en libros vivos,
  2026-10-25), funding real cobrado donde existe; los libros maker intra-bar
  **no** son certificables sobre OHLC ≥ 5m sin fills a 1m o registro forward.
- Concentración (los 5 mejores trades vs PnL total), split por tercios,
  control de coste cero dentro de cada artefacto.

### Qué hay vivo hoy

- **El book paper neutral** (delta-neutral two-sided grid) corre en un VPS
  como bot separado (5 pares, ciclo 15m + contabilidad a 1m). PAPER ONLY:
  sin órdenes, sin claves. Su lección más dura: la convención de fills del
  OHLC de 15m resultó ser una fabricación (el PF 1.30 midió 0.93 al
  resolver los toques en orden temporal real de 1m) — por eso existe la
  regla del modelo de fills.
- **El grabador** (`recorder/`) acumula cinta de order-flow para el track
  que necesita datos que ningún archivo público provee.
- **La cadena de master prompts**: v5.2 (ingeniería de indicadores — medir
  si una señal informa) → v6.1 (puente de graduación a edge transable) →
  batería de gates del repo (veredicto). Un `INFORMATIVE` de indicador no
  es un pass del repo: no lleva `run_id` y es otro estimando.

### Cómo verificar un número

1. Consigue los mismos datos públicos de Binance (klines + funding) — los
   scripts `code/fetch_*.py` muestran los endpoints; los datos no se
   redistribuyen.
2. `python code/vrun.py run --strategy <adaptador> --tf <tf> --symbol <par>`
   reproduce el artefacto; `python code/vrun.py verify <run_id>` lo prueba.
3. `python code/x_spec_check.py` verifica que cada token numérico de
   `content/specs.md` existe en el archivo fuente citado.

### Leer los veredictos

KILLED / REJECTED / FAIL / SUSPENDED / CANDIDATE — leyenda completa en
`GATES_AND_RULES.md`. Un CANDIDATE es un sobreviviente de criba, nunca un
edge probado. **Ninguna estrategia de este repo se vende como alfa; nada es
consejo financiero.** Fuentes de verdad: `AGENTS.md` (reglas y estado),
`STATUS.md` (historial completo de veredictos), `VALIDATION_PROTOCOL.md`,
`code/MAP.md` (qué es cada archivo y qué está fijado por hash),
`results/REPORTS.md` y `results/registry/`.

### Licencia

No license is granted. All rights reserved — read the code, but reuse of the
engines or reports is not permitted without permission.

---

## English

### What this repo is

A personal, **artifact-backed** backtest lab for public trading strategies on
crypto perpetuals (Binance USDⓈ-M, 1m–1d). The premise: a number is a result
only if a persisted run artifact backs it and that artifact **reproduces
bit-for-bit**. Everything else is text. The lab's real product is mostly
**negative**: of more than 1,700 strategies measured, the vast majority are
dead, and the repo documents why they died with evidence, not opinion.

State measured 2026-11-08: **5,342 artifacts** in `results/runs/`,
**1,721 strategies** in the registry, **43 engine adapters** in
`code/vrun.py`, **270** Python files in `code/`.

### REGLA 0 — no number without an artifact

The founding rule (born because an agent once reported a full backtest that
was never run):

- Every published metric cites its `run_id` — a hash of the engine bytes,
  the parameters and the data (time-cut: data appends no longer invalidate
  old artifacts).
- `verify` re-runs the engine and **refuses** unless the result is
  bit-for-bit identical. Exit codes: `0` OK · `2` REFUSED (tampered /
  non-reproducible) · `3` STALE (data bytes changed; re-run) · `4` ORPHANED
  (engine deleted from disk).
- `guard` rejects any report containing numbers no artifact backs.
- Synthetic / illustrative scenarios are labeled as such and never carry a
  `run_id`.

### REGLA 1 — one strategy, one verdict

Each strategy is judged **only** on its own artifacts. That a similar sibling
failed before is not evidence about this one: the kill list is history, never
a pre-gate.

### Layout

| Path | What it is |
|---|---|
| `code/` | Engines, harness (`vrun.py`), staged pipeline (`bt.py`), gates (GATES v2), audits, data tooling |
| `data/` | The only market source: Binance klines (1m–1d, taker variants), funding, aggTrades, Alpaca equities; integrity manifests (`FUNDING_MANIFEST.json`, `KLINES_MANIFEST.json`, …) |
| `results/runs/` | The artifacts (not shipped in the public release; `run_id`s and the registry reference them) |
| `results/registry/` | The universe: one row per measured strategy, with verdicts, cost regime and fill model; views by symbol/tf/family |
| `results/REPORTS.md` | Report index with `guard` status — only OK reports are citable |
| `edge/` | The sealed EDGE project (v4.1, terminal verdict) + the master prompts (v5.2 indicators → v6.1 edge bridge) |
| `recorder/` | Live order-flow recorder (bookTicker, depth, liquidations) for the recorded-data track |
| `pine/` | Pine script library (reference and audit) |
| `content/` | `specs.md` (the exact recipe of every posted strategy) and the X threads |
| `backups/`, `audit/` | History and independent-audit kits |

### The harness

```powershell
python code\vrun.py run    --strategy sax --tf 1h --symbol BTCUSDT   # run → artifact
python code\vrun.py render <run_id>    # numbers come ONLY from the artifact
python code\vrun.py verify <run_id>    # re-runs; REFUSED unless bit-for-bit identical
python code\vrun.py guard  --report report.md --strict
python code\vrun.py matrix --strategy sax --workers 4
python code\vrun.py stats  <run_id>    # institutional scorecard
python code\bt.py one --strategy <s> --tf <tf> --symbol <sym>  # one artifact, one battery, one verdict
```

### The gates

- **Screen**: ex-cost PF > 1.2, n ≥ 30 closed trades, green in ≥ 2/3 of
  years, neighborhood stability, walk-forward/OOS. **OOS PF < 1 = KILL**, no
  rescue loops.
- **Full battery**: `GATES_AND_RULES.md` (v2, G1–G11): n ≥ 100 for a full
  verdict, expectancy Ljung-Box, walk-forward folds, cost < 30%, win-rate
  breakeven, null calibration.
- **Costs**: 11 bps directional round trip (measured on live books,
  2026-10-25), real funding charged where it exists; resting-maker intra-bar
  books are **not** certifiable on OHLC ≥ 5m without 1m fills or a forward
  record.
- Concentration (best five trades vs total PnL), thirds split, zero-cost
  control measured inside each artifact.

### What is alive today

- **The neutral paper book** (delta-neutral two-sided grid) runs on a VPS as
  a separate bot (5 pairs, 15m cycle + 1m accounting). PAPER ONLY: no
  orders, no keys. Its hardest lesson: the 15m OHLC fill convention turned
  out to be a fabrication (PF 1.30 measured 0.93 once touches were resolved
  in true 1m temporal order) — which is why the fill-model rule exists.
- **The recorder** (`recorder/`) accumulates order-flow tape for the track
  that needs data no public archive provides.
- **The master-prompt chain**: v5.2 (indicator engineering — measure whether
  a signal informs) → v6.1 (graduation bridge to tradable edge) → the
  repo's gate battery (verdict). An indicator's `INFORMATIVE` is not a repo
  pass: no `run_id`, different estimand.

### How to verify a number

1. Get the same public Binance data (klines + funding) — the
   `code/fetch_*.py` scripts show the endpoints; data itself is not
   redistributed.
2. `python code/vrun.py run --strategy <adapter> --tf <tf> --symbol <pair>`
   reproduces the artifact; `python code/vrun.py verify <run_id>` proves it.
3. `python code/x_spec_check.py` verifies every numeric token in
   `content/specs.md` exists in its cited source file.

### Reading the verdicts

KILLED / REJECTED / FAIL / SUSPENDED / CANDIDATE — full legend in
`GATES_AND_RULES.md`. A CANDIDATE is a screen survivor, never a proven edge.
**No strategy in this repo is sold as alpha; nothing is financial advice.**
Sources of truth: `AGENTS.md` (rules and state), `STATUS.md` (full verdict
history), `VALIDATION_PROTOCOL.md`, `code/MAP.md` (what every file is and
what is hash-locked), `results/REPORTS.md` and `results/registry/`.

### License

No license is granted. All rights reserved — read the code, but reuse of the
engines or reports is not permitted without permission.
