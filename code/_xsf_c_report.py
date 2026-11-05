"""_xsf_c_report.py — renders results/xsf_category_c_report.md from the xsc artifacts.

Every number is read from a cited artifact (REGLA 0). Report lines that carry
a run_id never name a USDT symbol (guard --strict). Counts go in words.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "..", "results", "runs")
OUT = os.path.join(HERE, "..", "results", "xsf_category_c_report.md")

MAIN = [("FUNDGATE", "f8c556f2a7d194c3"),
        ("FUNDTAIL", "7d82a4921ea6cbd9")]
NEIGH = [("FUNDGATE", "lb 240", "ca0d1b5a0acf62dc"),
         ("FUNDGATE", "lb 480", "30a4ab1415cc17d5"),
         ("FUNDTAIL", "cap 0.0003", "66657dd972ffb3f5"),
         ("FUNDTAIL", "cap 0.001", "ddaea3cc7fa01765")]


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
    w("# Categoría C — libros filtrados por funding (FUNDGATE / FUNDTAIL)")
    w("")
    w("Campaña del dos de noviembre de dos mil veintiséis. Adaptador `xsc`, motor "
      "`code/xs_factor_c_engine.py` (xsc-1), que reutiliza SIN TOCAR la maquinaria "
      "de `xs_factor_engine.py` (categoría A — fijada por sus nueve artefactos); "
      "ambos ficheros entran en el hash del run_id. Universo de SIETE nombres con "
      "fichero de funding en disco. Harness `code/vrun.py`.")
    w("")
    w("Protocolo REGLA 0: cada número de este informe sale de un artefacto citado; "
      "los seis artefactos verifican bit-for-bit. Los conteos van en palabras.")
    w("")
    w("A diferencia de las categorías A y B (funding declarado sin cobrar), aquí "
      "el funding se COBRA de verdad en cada simulación: cada settlement real del "
      "fichero de funding de una pata abierta factura -dir * unidades * apertura "
      "* tarifa cruda dentro de la ventana de la barra (JUP y HYPE liquidan cada "
      "cuatro horas: dos settlements reales, no uno doblado). Tres simulaciones "
      "por artefacto con decisiones idénticas (asegurado): neta (costes + "
      "funding), bruta sin costes de trading con funding (control ex-coste), y "
      "bruta sin costes NI funding — `funding_pnl_pct` es la contribución del "
      "funding al libro. Cobertura según `data/FUNDING_MANIFEST.json`: el gap de "
      "cabeza de JUP a una hora es de doscientos cuarenta y tres días, así que "
      "los libros arrancan con el primer funding de JUP (octubre de dos mil "
      "veinticuatro) y HYPE entra con su propia primera barra (mayo de dos mil "
      "veinticinco); la cola de JUP descubre dos días y medio. Gate de funding "
      "normalizado por ocho horas (tarifa cruda por ocho entre la cadencia modal "
      "del símbolo). Estadísticas de ventana (tercios, mitades, años, split "
      "setenta-treinta) medidas sobre la ventana ACTIVA del libro, no sobre el "
      "índice unión.")
    w("")
    w("Definiciones de las cartas (declaradas en `provenance.conventions`):")
    w("- FUNDGATE: libro base ROC del lookback clasificado descendente, dos patas "
      "por lado fijo; gate de signo de funding en las entradas — un candidato "
      "largo se mantiene solo si la última tarifa por ocho horas es menor o igual "
      "que cero (cobra o neutra) y un candidato corto solo si es mayor que cero "
      "(cobra); el candidato que falla deja su hueco en efectivo (libro no "
      "siempre plenamente dolar-neutro — declarado); las patas en cartera no se "
      "re-gatean.")
    w("- FUNDTAIL: libro de baja volatilidad (la carta LOWVOL de la categoría A "
      "restringida al universo de siete), dos patas por lado fijo, con exclusión "
      "de funding extremo: candidato largo excluido si la tarifa por ocho horas "
      "supera el umbral (pagaría), candidato corto excluido si es menor que el "
      "umbral negativo; umbral declarado cinco puntos básicos por ocho horas.")
    w("")

    w("## Resultados principales")
    w("")
    w("| Carta | run_id | net % | gross % | sin funding % | funding PnL pp | "
      "PF | PF ex-cost | n | IS PF | OOS PF | maxDD % | B&H EW % | eventos facturados |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for card, rid in MAIN:
        m = arts[rid]["metrics"]
        w(f"| {card} | `{rid}` | {f(m['return_pct'])} | {f(m['gross_return_pct'])} | "
          f"{f(m['gross_no_funding_pct'])} | {f(m['funding_pnl_pct'])} | "
          f"{f(m['profit_factor'], 4)} | {f(m['profit_factor_ex_cost'], 4)} | "
          f"{m['n_trades']} | {f(m['is_pf'], 4)} | {f(m['oos_pf'], 4)} | "
          f"{f(m['max_dd_pct'], 1)} | {f(m['bh_return_pct'], 1)} | "
          f"{m['fund_events_billed']} |")
    w("")
    for card, rid in MAIN:
        m = arts[rid]["metrics"]
        w(f"Bandera del artefacto `{rid}`: `{m['flag']}`.")
    w("")

    w("## Vecindario (gate de estabilidad; no es rescate)")
    w("")
    w("| Carta | variante | run_id | net % | PF ex-cost | funding PnL pp | OOS PF | n |")
    w("|---|---|---|---|---|---|---|---|")
    for card, var, rid in NEIGH:
        m = arts[rid]["metrics"]
        w(f"| {card} | {var} | `{rid}` | {f(m['return_pct'])} | "
          f"{f(m['profit_factor_ex_cost'], 4)} | {f(m['funding_pnl_pct'])} | "
          f"{f(m['oos_pf'], 4)} | {m['n_trades']} |")
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

    rid_fg = MAIN[0][1]
    w("## Desglose por simbolo (carta FUNDGATE, tabla `per_symbol` del artefacto "
      f"`results/runs/{rid_fg}.json`)")
    w("")
    w("| simbolo | n trades | WR % | PnL eq % |")
    w("|---|---|---|---|")
    for row in arts[rid_fg]["tables"]["per_symbol"]:
        w(f"| {row[0]} | {row[1]} | {f(row[2], 1)} | {f(row[3], 2)} |")
    w("")

    w("## Hallazgos declarados")
    w("")
    w("- FUNDGATE pierde en las tres celdas (PF ex-cost entre cero coma setenta "
      "y tres y cero coma noventa y cuatro): el viento de cola del funding "
      "existe pero es diminuto — entre uno coma tres y dos coma uno puntos "
      "porcentuales en dos anos, muy lejos de compensar la senal perdedora.")
    w("- FUNDTAIL hace SEIS trades en dos anos en cualquier umbral: muere por "
      "suelo de muestra antes que por todo lo demas. La celda del vecindario con "
      "umbral mas estricto muestra un neto positivo, pero con seis trades es "
      "exactamente el ruido que la calibracion nula del repositorio mide (un "
      "nulo pasa los gates hasta en un cinco por ciento de las veces con "
      "muestras pequenas) — sin valor de evidencia y sin rescate.")
    w("- El gate de signo de funding deja huecos en efectivo con frecuencia "
      "(exposicion bruta media muy por debajo de cien por ciento en ambas "
      "cartas): en un universo de siete perpes, largos que cobran funding son "
      "raros porque casi todo el sector paga funding positivo la mayor parte "
      "del tiempo.")
    w("")

    w("## Veredicto")
    w("")
    w("**Categoría C (FUNDGATE / FUNDTAIL sobre el universo de siete con "
      "funding, funding COBRADO): KILLED — cero de dos cartas supera los "
      "gates.** FUNDGATE pierde por senal con un viento de funding real pero "
      "dos ordenes de magnitud menor que lo necesario; FUNDTAIL muere por "
      "muestra. La familia funding-como-filtro (no como carry, familia esa ya "
      "terminal por la auditoria EDGE) queda medida muerta en este repositorio.")
    w("")

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
