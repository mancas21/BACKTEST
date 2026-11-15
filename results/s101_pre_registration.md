# s101 — pre-registro de campaña (congelado antes de la primera corrida)

Fecha de congelación: 2026-11-13. Pack adjunto: STRATEGIES 101-150 (50 prompts;
fuente de registro byte-idéntica `code/prompts_101_150.txt`, sha en el manifiesto
de la campaña). Adaptador `s101`, motor `code/s101_engine.py` sobre el núcleo de
ejecución `Book` de `code/p100_screen_engine.py` (ya auditado por la campaña
p100). Regla del propio pack #19 aplicada en el triaje: si falta el dato, se
salta; no se finge.

## Triaje de datos (50 prompts)

CORREN (37): 101-108, 109, 110, 112, 115, 116-122, 123-131, 133, 134, 135,
138-140, 141, 144, 150.
NO-DATA (13, se saltan con declaración): 111 (liquidaciones — solo ~2 meses de
grabadora), 113 (open interest — ~20 días), 114 (spot ETH ausente), 132
(calendario macro), 136 (tick data), 137 (order book), 142 (NVDA 1m ausente),
143 (NVDA 3m requiere 1m), 145 (SMH ausente), 146 (SPCX 1m ausente), 147 (SPY
ausente), 148 (VIX ausente), 149 (breadth ausente).

## Convenciones de ejecución (declaradas, iguales para las 37 celdas)

- Señal al cierre de la barra; entrada en la APERTURA de la barra siguiente;
  stop-first si stop y target tocan la misma barra; gap que cruza el stop llena
  en la apertura (stop_gap). Idéntico a las reglas #1-2 del pack y al núcleo
  Book auditado.
- **Costes: régimen repo uniforme 5 bps fee + 0.5 bps slip por lado = 11 bps
  RT en TODAS las celdas** — desviación declarada del calendario por símbolo
  del pack (10-18 bps RT); el régimen repo es la puerta de casa y queda dentro
  del rango que el propio pack declara.
- Riesgo 0.5% del equity por trade (regla #4 del pack), sin martingala;
  tamaño qty = riesgo / distancia al stop, capado a 3x equity de nocional.
- Contadores diarios del pack #5: máximo 3 trades perdedores por día UTC y
  máximo 6 trades por día en books de 1m/3m; ambos evaluados causalmente.
- Funding cobrado en los settlements reales para los 7 perps (ficheros del
  repo); NVDA/SPCX sin fichero de funding: NO cobrado, declarado.
- Sin trailing stop en ninguna celda (regla #6 del pack).
- IS/OOS: 70/30 cronológico sin purga (regla #17 del pack, declarada).
- Las reglas #16-17 del pack ("OOS n < 200 → frágil") son etiqueta de informe;
  la batería de gates es la de casa.
- Ventana por celda: todo el historial disponible del símbolo/TF en disco
  (NVDA/SPCX: ~4-6 meses — frágiles por la regla #18 del propio pack).

## Gates (pantalla estándar de casa, via bt.py)

profit_factor > 1.2; n_trades ≥ 30; return_pct > 0; n_periods_green ≥ 2;
oos_profit_factor > 1.2; oos_return_pct > 0; top5_pnl_share ≤ 100; boot_ci_lo
> 0. OOS PF < 1 = KILL (regla de casa). REGLA 1: cada celda = un veredicto
sobre sus propios artefactos; el fallo de un hermano no es evidencia.
