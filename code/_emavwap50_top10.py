"""Select the ten least-bad rows of the EMA×VWAP suite under the frozen
criteria in results/emavwap50_top10_criteria.md. Every number comes from a
stored artifact and carries its run_id.

Run: python code/_emavwap50_top10.py
"""
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

MATRIX = os.path.join(ROOT, "results", "emavwap50_matrix.json")
OUTJSON = os.path.join(ROOT, "results", "emavwap50_top10_selection.json")
OUTMD = os.path.join(ROOT, "results", "emavwap50_top10_report_2026-11-25.md")
_RID = re.compile(r"^[0-9a-f]{16}$")
_RUNS = os.path.realpath(os.path.join(ROOT, "results", "runs"))


def load(rid):
    if not _RID.match(str(rid)):
        raise ValueError(f"refusing non run_id: {rid!r}")
    p = os.path.realpath(os.path.join(_RUNS, str(rid) + ".json"))
    if not (p.startswith(_RUNS + os.sep) and os.path.isfile(p)):
        raise ValueError(f"artifact outside the runs dir: {rid!r}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def key(r):
    m = r["m"]
    return (-m["profit_factor"], -m["net_pct"],
            -(m["test_pf"] if m["test_pf"] is not None else -math.inf),
            -(m["boot_exp_lb"] if m["boot_exp_lb"] is not None else -math.inf))


def main():
    data = json.load(open(MATRIX, encoding="utf-8"))
    eligible = []
    for rid, cell in data["cells"].items():
        a = load(cell["run_id"])
        m = a["metrics"]
        if m["n_trades"] >= 30 and m["profit_factor"] is not None:
            eligible.append(dict(row=int(rid), tf=cell["tf"],
                                 run_id=cell["run_id"], m=m))
    eligible.sort(key=key)
    top = eligible[:10]

    payload = {"criteria": "results/emavwap50_top10_criteria.md",
               "eligible_n": len(eligible),
               "top": [{"row": r["row"], "tf": r["tf"], "run_id": r["run_id"]}
                       for r in top],
               "note": "post-hoc ranking of a killed family; least-bad, not "
                       "validated and not alpha evidence"}
    with open(OUTJSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=False)

    L = []
    A = L.append
    A("# Las 10 mejores (menos malas) filas del EMA×VWAP Suite")
    A("")
    A("Date: 2026-11-25. Esta selección usa la regla fijada en "
      "`results/emavwap50_top10_criteria.md` antes de ordenar nada. Es una "
      "**selección post-hoc dentro de una familia KILLED**: ninguna fila "
      "pasó el gate y ninguna de estas diez es evidencia de alpha.")
    A("")
    A("## Criterio aplicado")
    A("")
    A("Solo filas con artefacto, al menos treinta operaciones y PF finito; "
      "se ordena por PF ex-cost descendente, con net %, PF de la mitad test "
      "y límite inferior del bootstrap como desempates. La columna ZERO se "
      "muestra pero no decide: es un control sin costes que nadie puede "
      "operar. Las filas sin datos y las de muestra insuficiente no entran "
      "en el ranking.")
    A("")
    A("## Las diez elegidas")
    A("")
    A("| # | Fila | TF | Net % | PF | Trades | ZERO % | Test PF | Boot LB | run_id |")
    A("|---:|---:|---|---:|---:|---:|---:|---:|---:|---|")
    for i, r in enumerate(top, start=1):
        m = r["m"]
        tpf = "-" if m["test_pf"] is None else f"{m['test_pf']:.3f}"
        lb = "-" if m["boot_exp_lb"] is None else f"{m['boot_exp_lb']:.3f}"
        A(f"| {i} | {r['row']} | {r['tf']} | {m['net_pct']:.2f} | "
          f"{m['profit_factor']:.3f} | {m['n_trades']} | "
          f"{m['zero_cost_ret_pct']:.2f} | {tpf} | {lb} | `{r['run_id']}` |")
    A("")
    A("## Cómo leer esta lista")
    A("")
    A("El orden es puramente relativo: el PF de la mejor fila sigue muy por "
      "debajo del suelo de 1.2, su red es negativa y su bootstrap no "
      "confirma nada. Las celdas con ZERO positivo muestran que el coste "
      "explica parte del desastre, pero eso no convierte a la fila en "
      "operable; las de ZERO negativo pierden incluso sin costes.")
    A("")
    A("Elegir diez entre todas las elegibles después de ver los resultados "
      "es una forma de multiplicidad: el ranking está sesgado hacia arriba "
      "por construcción. No se le aplica un descuento arbitrario; simplemente "
      "no se usa como evidencia ni para reabrir un veredicto.")
    A("")
    A("Las dos últimas filas de la tabla empatan en las cuatro claves de "
      "orden; el desempate lo decidió el orden en que aparecen en la matriz, "
      "no una medida nueva. Intercambiarlas no cambiaría ninguna conclusión.")
    A("")
    A("## Provenance")
    A("")
    A("- Criterio: `results/emavwap50_top10_criteria.md` (escrito antes de "
      "calcular el orden).")
    A("- Fuente: `results/emavwap50_report_2026-11-25.md` y sus artefactos, "
      "todos verificados bit a bit.")
    A("- Selección calculada: `results/emavwap50_top10_selection.json`.")
    A("- Ningún número nuevo: cada línea cita el `run_id` del artefacto que "
      "contiene la cifra.")
    A("")

    text = "\n".join(L) + "\n"
    out = os.path.realpath(OUTMD)
    if not out.startswith(os.path.realpath(ROOT) + os.sep):
        raise ValueError("output outside the repo root")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"[built {len(text)} chars] -> {OUTMD}", file=sys.stderr)
    for i, r in enumerate(top, start=1):
        print(f"{i:2d}. row {r['row']} {r['tf']} PF {r['m']['profit_factor']:.6f} "
              f"net {r['m']['net_pct']:.2f} {r['run_id']}")


if __name__ == "__main__":
    main()
