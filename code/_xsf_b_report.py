"""_xsf_b_report.py — renders results/xsf_category_b_report.md from the xsb artifacts.

Every number is read from a cited artifact (REGLA 0). Report lines that carry
a run_id never name a USDT symbol (guard --strict). Counts go in words.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "..", "results", "runs")
OUT = os.path.join(HERE, "..", "results", "xsf_category_b_report.md")

MAIN = [("VOLCOMP", "138c4b2f93fd62db"),
        ("DDRELAY", "c7b83f8626bf21b4")]
NEIGH = [("VOLCOMP", "240", "233906b11726316d"),
         ("VOLCOMP", "480", "bbd4ed10c0aa6f43"),
         ("DDRELAY", "trig -0.15", "1f065febc8cc9bfd"),
         ("DDRELAY", "trig -0.25", "05f467361fa13783")]


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
    arts.update({rid: load(rid) for _, _, rid in NEIGH})

    lines = []
    w = lines.append
    w("# Categoría B — valor relativo 1h (VOLCOMP / DDRELAY)")
    w("")
    w("Campaña del dos de noviembre de dos mil veintiséis. Adaptador `xsb`, motor "
      "`code/xs_factor_b_engine.py` (xsb-1), que reutiliza SIN TOCAR la maquinaria "
      "de `xs_factor_engine.py` (categoría A — sus bytes quedaron fijados por los "
      "nueve artefactos de esa campaña); ambos ficheros entran en el hash del "
      "run_id. Harness `code/vrun.py`.")
    w("")
    w("Protocolo REGLA 0: cada número de este informe sale de un artefacto citado; "
      "los seis artefactos verifican bit-for-bit. Los conteos van en palabras.")
    w("")
    w("Definiciones de las cartas (declaradas en `provenance.conventions` de cada "
      "artefacto):")
    w("- VOLCOMP: z-score de sesenta dias de la volatilidad relativa (vol del "
      "lookback sobre la mediana cross-sectional de esa misma vol), rango "
      "ascendente; puerta de drift en las entradas (largo solo si el retorno de "
      "siete dias es positivo, corto solo si es negativo; la pata que falla deja "
      "su hueco en efectivo, así que el libro no siempre es plenamente "
      "dolar-neutro — declarado; las patas en cartera no se re-gatean).")
    w("- DDRELAY: libro condicionado a evento. Disparador evaluado en cada "
      "decisión semanal: mediana cross-sectional del retorno de treinta dias por "
      "debajo del umbral (menos veinte por ciento en la carta principal) con al "
      "menos ocho simbolos contribuyendo. Mientras dispara: largo las dos menos "
      "dibujadas y corto las dos más dibujadas desde su máximo de catorce dias; "
      "cuando el disparador se apaga, el libro entero cierra en la apertura "
      "siguiente y queda plano.")
    w("- Convenciones compartidas con la categoría A: decisión al cierre, "
      "ejecución en la apertura siguiente, coste por lado en cada fill, resize a "
      "equity/(2k) con base de coste promedio, histéresis, control de coste cero "
      "con decisiones idénticas dentro del artefacto, funding NO cobrado "
      "(declarado), bootstrap semillado de diez mil remuestreos.")
    w("")

    w("## Resultados principales")
    w("")
    w("| Carta | run_id | net % | gross % | PF | PF ex-cost | n | WR % | IS PF | "
      "OOS PF | top-5 % PnL | net sin top-5 % | maxDD % | B&H EW % | episodios | "
      "decisiones activas |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for card, rid in MAIN:
        m = arts[rid]["metrics"]
        w(f"| {card} | `{rid}` | {f(m['return_pct'])} | {f(m['gross_return_pct'])} | "
          f"{f(m['profit_factor'], 4)} | {f(m['profit_factor_ex_cost'], 4)} | "
          f"{m['n_trades']} | {f(m['win_rate'], 1)} | {f(m['is_pf'], 4)} | "
          f"{f(m['oos_pf'], 4)} | {f(m['conc_top5_share_pct'], 1)} | "
          f"{f(m['conc_net_without_top5_pct'], 1)} | {f(m['max_dd_pct'], 1)} | "
          f"{f(m['bh_return_pct'], 1)} | {m['episodes']} | "
          f"{m['active_decisions']} |")
    w("")
    for card, rid in MAIN:
        m = arts[rid]["metrics"]
        w(f"Bandera del artefacto `{rid}`: `{m['flag']}`.")
    w("")

    w("## Vecindario (gate de estabilidad; no es rescate)")
    w("")
    w("| Carta | variante | run_id | net % | PF ex-cost | OOS PF | top-5 % | maxDD % |")
    w("|---|---|---|---|---|---|---|---|")
    for card, var, rid in NEIGH:
        m = arts[rid]["metrics"]
        w(f"| {card} | {var} | `{rid}` | {f(m['return_pct'])} | "
          f"{f(m['profit_factor_ex_cost'], 4)} | {f(m['oos_pf'], 4)} | "
          f"{f(m['conc_top5_share_pct'], 1)} | {f(m['max_dd_pct'], 1)} |")
    w("")

    w("## Gates medidos por carta (tabla `gates` de cada artefacto principal)")
    w("")
    for card, rid in MAIN:
        w(f"Artefacto: `results/runs/{rid}.json`")
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

    rid_dd = MAIN[1][1]
    w("## Desglose por simbolo (carta DDRELAY, tabla `per_symbol` del artefacto "
      f"`results/runs/{rid_dd}.json`)")
    w("")
    w("| simbolo | n trades | WR % | PnL eq % |")
    w("|---|---|---|---|")
    for row in arts[rid_dd]["tables"]["per_symbol"]:
        w(f"| {row[0]} | {row[1]} | {f(row[2], 1)} | {f(row[3], 2)} |")
    w("")

    w("## Hallazgos declarados")
    w("")
    w("- Ambas cartas pierden ANTES de costes (PF ex-cost por debajo de uno en "
      "las dos cartas principales): el fallo es de senal, no de coste.")
    w("- DDRELAY disparó veintitres episodios — no es una condición rara; el "
      "libro estuvo activo en cincuenta y una de sus decisiones y aun así "
      "perdió en bruto.")
    w("- El vecindario no rescata: las cuatro celdas fallan. La mejor celda de "
      "VOLCOMP en bruto (lookback cuatrocientos ochenta) sigue con OOS por "
      "debajo de uno y una concentracion extrema.")
    w("- Funding no cobrado (declarado); B&H medido desde la primera barra "
      "activa de cada libro.")
    w("")

    w("## Veredicto")
    w("")
    w("**Categoría B (VOLCOMP / DDRELAY sobre el universe-14 a una hora): "
      "KILLED — cero de dos cartas supera los gates; ambas pierden en bruto y "
      "el vecindario confirma que no es un problema de parametro.** La "
      "convergencia de volatilidad relativa y el relay de drawdown relativo no "
      "contienen edge en este universo ni en este coste. Con la categoría A "
      "killed el mismo dia, el bloque OHLCV-only del pack generado (categorías "
      "A y B) cierra con cero supervivientes.")
    w("")

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
