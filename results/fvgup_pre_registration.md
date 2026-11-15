# fvgup — pre-registro de campaña (congelado antes de la primera corrida)

Fecha de congelación: 2026-11-13. Pack: `code/fvg_system.py` (base ICT 4H FVG →
15M FVG, fuente de registro byte-idéntica del adjunto) + `code/fvg_upgrades.py`
(extensiones: resolución intrabar 1m + sesiones/liquidez DST). Adaptador `fvgup`,
motor `code/fvgup_engine.py`. Batería: pantalla estándar del repo (PF ex-cost >
1.2, n ≥ 30, tercios verdes ≥ 2/3, OOS PF ≥ 1 — OOS PF < 1 = KILL —,
concentración top-5 < 100% y neta sin top-5 > 0, comparación vs B&H, G11).
REGLA 1: el veredicto sale de ESTOS artefactos y de nada más.

## Ventana

15m y 1m recortados a la ventana cubierta por 1m: **[2023-01-01, 2026-10-01)**
— así cada barra de 15m es resoluble en la cinta de 1m (`fine_strict`). Fuera de
la ventana no se publica nada.

## Costes (inyectados por el llamador, jamás editando los motores)

- fee_maker = fee_taker = 0.0005 (5 bps por lado), slip_bps = 0.5 (0.5 bps
  adverso en salidas taker) → 11.0 bps ida y vuelta en salidas taker, 10.5 en
  salidas maker. Entradas son LIMIT maker en el borde proximal de la FVG 15m;
  stop/time/gap son taker; target es maker.
- **Funding: el modelo del pack es de tarifa constante** (`funding_bps_8h=1.0`:
  largos pagan 1 bp por 8h, cortos cobran) — una APROXIMACIÓN declarada; el
  motor no es editable y el repo sí tiene funding real por settlement. Se
  publican `fees_total` y `funding_total` medidos dentro del artefacto, y el PF
  ex-cost se calcula POR TRADE (pnl + fees + funding) sobre la misma corrida —
  decisión-idéntico por construcción, sin segunda corrida.
- Config restante: defaults del pack congelados (tp_r 2.0, riesgo 0.5%/trade,
  max leverage 3x, BE en 1R, parcial 50% a 1R, trailing desde 2R con ATR 2,
  max_hold 96 barras, one_trade_per_htf, kill switches 3%/20%).

## Celdas (cuatro, sin rejilla)

| carta | símbolo | fill | sesiones | certificabilidad |
|---|---|---|---|---|
| BTCFINE | BTCUSDT | limit resuelto en cinta 1m (fine) | ON (London+NY-AM, findes fuera, cancelación fuera de sesión) | CERTIFICABLE (resolución 1m) |
| BTCCOARSE | BTCUSDT | convención 15m same-bar | ON | NO certificable (regla fill-model) — comparación |
| BTCNOSESS | BTCUSDT | fine | OFF (ablación de la mejora #2) | CERTIFICABLE |
| ETHFINE | ETHUSDT | fine (tick_size 0.01) | ON | CERTIFICABLE |

## Contrato dentro de cada artefacto

1. `parity_check_v2` del propio pack (motor vector vs motor de eventos, sesiones
   ON, modo simple) sobre los bytes reales: debe MATCH — si no, el artefacto se
   niega a existir.
2. Auditoría de integridad del fine (agregado 1m vs barra 15m, tolerancia
   0.5 bps): `pct_usable` publicado; celdas fine exigen ~100%.
3. Invariante contable asertado: equity final − inicial == Σpnl − Σfunding
   (el pack cobra el funding fuera del pnl del trade); residual publicado.
4. Stats del motor (fine_bars/coarse_bars/ambiguous/session_cancels) publicados.

## Veredicto

PASS solo si todas las gates pasan en la celda; cada celda es un veredicto
propio (REGLA 1). El veredicto de campaña agrega con conteos en palabras.

## ADICIÓN (2026-11-13, antes de la primera corrida) — paridad del pack FALLIDA en datos reales

`parity_check_v2` (motor vector vs motor de eventos, sesiones ON, modo simple)
FALLA sobre los bytes reales de la ventana: vector=27 vs evento=28 trades en
BTC 15m (2023-01..2026-10) — un trade LONG solo del motor de eventos (entry
56331.8, fill 2024-09-11 08:30 UTC, bars=0). Mecanismo medido: los dos motores
discrepan en la semántica de re-arme de una zona viva — el motor vector salta
por eventos y reinicia la secuencia de touch desde su posición de llegada (un
touch anterior a su llegada no se re-considera); el motor de eventos camina
barra a barra y vio ese touch. Un parche de una línea (resetear el estado en
la invalidación de zona, semántica vector) se probó y NO resolvió la
divergencia — se revirtió; la reconciliación es una decisión de diseño del
autor del pack.

DECISIÓN declarada: la campaña publica el MOTOR DE EVENTOS (el de producción,
"live-ready") con la divergencia medida trade-a-trade y declarada dentro de
cada artefacto (`parity_ok`, tablas `parity_divergence`); la verificación
dual-motor del pack NO se da por válida hasta que el autor reconcilie. El
veredicto de cada celda lleva esta advertencia impresa.
