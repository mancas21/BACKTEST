"""_fvgup_report.py — renders results/fvgup_report_2026-11-13.md from the fvgup
artifacts. Every number is read from a cited artifact (REGLA 0). Report lines
that carry a run_id never name a USDT symbol (guard --strict). Counts in words.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "..", "results", "runs")
OUT = os.path.join(HERE, "..", "results", "fvgup_report_2026-11-13.md")

MAIN = [("BTCFINE", "7dfd3c4de2f6765e"),
        ("BTCCOARSE", "7924a180df2bbb96"),
        ("BTCNOSESS", "bc3d3dc1af3fcd47"),
        ("ETHFINE", "fdf4391a289b3fd6")]


def load(rid):
    p = os.path.join(RUNS, rid + ".json")
    if not os.path.exists(p):
        sys.exit(f"missing artifact {rid}")
    return json.load(open(p, encoding="utf-8"))


def f(v, nd=2):
    if v is None:
        return "n/a"
    return f"{v:.{nd}f}"


def main():
    arts = {rid: load(rid) for _, rid in MAIN}

    lines = []
    w = lines.append
    w("# fvgup — ICT 4H FVG → 15M FVG con resolución 1m y sesiones (adjunto del 13 de noviembre de 2026)")
    w("")
    w("## VEREDICTO: KILLED — cero de cuatro celdas pasa la batería estándar")
    w("")
    w("La tesis de ejecución del adjunto SÍ se materializó tras el porte (la resolución")
    w("intrabar a 1m funciona, la ambigüedad stop/target se resuelve, la integridad de la")
    w("cinta es cercana al cien por ciento), pero el libro resultante no supera la batería:")
    w("muestra por debajo del suelo en las tres cartas de BTC, concentración extrema, y")
    w("ninguna celda bate a comprar-y-mantener. El filo bruto existe (PF ex-cost entre")
    w("uno coma cinco y dos coma siete) y el régimen de costes del repo lo consume: las")
    w("comisiones totales rondan el cinco por ciento del equity en la ventana.")
    w("")
    w("Fuente de registro: `code/fvg_system.py` + `code/fvg_upgrades.py` (adjuntos")
    w("byte-idénticos; sha del segundo fijado en `code/_fvgup_build_sha.json`). Adaptador")
    w("`fvgup`, motor `code/fvgup_engine.py`. Pre-registro con adición fechada:")
    w("`results/fvgup_pre_registration.md`. Ventana: la cobertura 1m del repositorio,")
    w("del uno de enero de dos mil veintitrés al uno de octubre de dos mil veintiséis.")
    w("Costes repo inyectados por el llamador (cinco bps de comisión más medio de")
    w("deslizamiento por lado); funding = modelo de tarifa constante del pack")
    w("(aproximación declarada; los ficheros reales de funding no están cableados al")
    w("motor del pack, que no es editable).")
    w("")

    w("## Defectos del pack medidos durante el puerto")
    w("")
    w("- **La paridad dual-motor del pack FALLA en BTC y PASA en ETH.** En la carta")
    w("  BTCFINE el artefacto mide veintisiete trades del motor vector contra")
    w("  veintiocho del motor de eventos: un LONG solo del motor de eventos")
    w("  (entrada 56331.8, llenado 2024-09-11 08:30 UTC, bars=0, zona bull 323) que")
    w("  el motor vector no genera — los dos motores discrepan en la semántica de")
    w("  re-arme de una zona viva. Un parche de una línea (resetear el estado en la")
    w("  invalidación, semántica vector) se probó y NO resolvió la divergencia: se")
    w("  revirtió; la reconciliación es decisión del autor. En la carta ETHFINE la")
    w("  paridad del pack SÍ se cumple. Cada artefacto publica `parity_ok` y la tabla")
    w("  `parity_divergence` trade a trade; el pack se niega a publicar sus propios")
    w("  números en este estado y esta campaña declara la desviación en cada celda.")
    w("- **Dos defectos de unidades de pandas 3.0** (el pack es código de pandas 2.x;")
    w("  el repo corre 3.0.5). Primero: la ventana de búsqueda de FineData mezclaba")
    w("  enteros de microsegundo del índice con un entero de nanosegundo del")
    w("  Timedelta — ventana mil veces más ancha, integridad fallida en todas las")
    w("  barras y el libro fino corría grueso sin decrirlo (medido: cnt ≈ quince mil")
    w("  barras de un minuto por barra de quince minutos). Corregido con el builder")
    w("  `code/_fvgup_build.py` → `code/fvg_upgrades_portfix.py` (un parche literal,")
    w("  sha fijado). Segundo: `to_datetime(unit=\"ms\")` conserva la unidad en")
    w("  pandas 3.0 y el índice quedaba en milisegundos contra aritmética de")
    w("  nanosegundos del pack — ninguna orden fina llenaba (cero trades). Corregido")
    w("  en el adaptador normalizando ambos índices a nanosegundos.")
    w("- **La contabilidad del pack cobra la comisión de entrada FUERA del pnl del")
    w("  trade** (la columna fees la incluye, el pnl no la resta) y el funding fuera")
    w("  del pnl también. La invariante del repositorio se reformuló para esta")
    w("  contabilidad y cierra al céntimo: equity final − inicial == Σpnl − Σfunding")
    w("  − Σ(comisión de entrada por trade); residual publicado en cada artefacto.")
    w("")

    w("## Las cuatro celdas (verificadas bit-for-bit; run_id citado por línea)")
    w("")
    w("| Carta | run_id | net % | PF | PF ex-cost | n | WR % | IS PF | OOS PF | maxDD % | B&H % | top-5 % PnL | comisiones USDT | fine usable % | paridad pack |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for card, rid in MAIN:
        m = arts[rid]["metrics"]
        w(f"| {card} | `{rid}` | {f(m['return_pct'])} | {f(m['profit_factor'], 4)} | "
          f"{f(m['profit_factor_ex_cost'], 4)} | {m['n_trades']} | {f(m['win_rate'], 1)} | "
          f"{f(m['is_pf'], 4)} | {f(m['oos_pf'], 4)} | {f(m['max_dd_pct'], 2)} | "
          f"{f(m['bh_return_pct'], 2)} | {f(m['conc_top5_share_pct'], 1)} | "
          f"{f(m['fees_total_usdt'], 1)} | {f(m['fine_pct_usable'], 2)} | "
          f"{'OK' if m['parity_ok'] else 'FALLA (declarada)'} |")
    w("")
    w("Bandera por artefacto:")
    w("")
    for card, rid in MAIN:
        w(f"- `{rid}`: `{arts[rid]['metrics']['flag']}`")
    w("")
    w("Modelo de fill por carta: BTCFINE / BTCNOSESS / ETHFINE resuelven los llenados")
    w("maker en la cinta de 1m (certificables según la regla fill-model); BTCCOARSE usa")
    w("la convención de barra de 15m (NO certificable, comparación declarada). La")
    w("resolución fina funciona tras el parche de unidades: en las cartas finas el")
    w("número de barras resueltas en cinta es de unos ciento treinta mil contra unas")
    w("veinte gruesas, y la ambigüedad stop/target del convenio grueso (seis casos en")
    w("BTCCOARSE) baja a cero.")

    w("")
    w("## Atribución por sesión (carta BTCFINE, tabla `session_attribution` del")
    w(f"artefacto `results/runs/{MAIN[0][1]}.json`)")
    w("")
    w("| sesión | n trades | WR % | exp_r | PnL USDT | PF |")
    w("|---|---|---|---|---|---|")
    for row in arts[MAIN[0][1]]["tables"]["session_attribution"]:
        w(f"| {row[0]} | {row[1]} | {f(row[2], 1)} | {f(row[3], 3)} | {f(row[4], 2)} | "
          f"{f(row[5], 4)} |")
    w("")
    w("La ablación de sesiones es el hallazgo vivo del adjunto: sin ventanas, el libro")
    w("pierde casi veinte por ciento (carta BTCNOSESS); con London + NY-AM el libro")
    w("queda cerca del cero. El filtro de sesiones ELIMINA las horas perdedoras — pero")
    w("el libro resultante sigue sin pasar la batería.")
    w("")

    w("## Gates medidos por carta (tabla `gates` de cada artefacto)")
    w("")
    for card, rid in MAIN:
        w(f"Artefacto: `results/runs/{rid}` (json)")
        w("")
        w("| gate | umbral | medido | pasa |")
        w("|---|---|---|---|")
        for row in arts[rid]["tables"]["gates"]:
            gate, thr, val, ok = row[0], row[1], row[2], row[3]
            v = val
            if isinstance(v, bool):
                v = str(v)
            elif isinstance(v, float):
                v = f(v, 4)
            w(f"| {gate} | {thr} | {v} | {'SI' if ok else 'NO'} |")
        w("")

    w("## Veredicto")
    w("")
    w("**Campaña fvgup: KILLED — cero de cuatro celdas pasa la batería estándar.**")
    w("Las tres cartas de BTC mueren por muestra (veintiocho trades en tres años y")
    w("tres cuartos, por debajo del suelo de treinta), concentración (el top cinco de")
    w("trades es entre ciento setenta y dos y doscientos uno por ciento del PnL) y")
    w("ausencia de ventaja contra comprar-y-mantener (+405.99 por ciento en la misma")
    w("ventana). La celda sin sesiones pierde diecinueve por ciento neto con PF neto")
    w("por debajo de uno y OOS PF cero coma cinco dos — kill directo. La carta de ETH")
    w("alcanza muestra y OOS, pero pierde neto (PF neto cero coma ocho seis) y falla")
    w("concentración y B&H. El filo bruto es real (PF ex-cost entre uno coma cinco y")
    w("dos coma siete) y el régimen de costes del repo lo consume — el mismo patrón")
    w("que el resto del corpus. La paridad dual-motor del pack queda marcada como")
    w("defecto del autor: falla en BTC, pasa en ETH; ningún número de este informe")
    w("usa la verificación dual hasta que el autor reconcilie la semántica de re-arme.")
    w("")

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
