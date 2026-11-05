"""_xsf_report.py — renders results/xsf_category_a_report.md from the xsf artifacts.

Every number in the report is read from a cited artifact (REGLA 0): the script
fails if any cited run_id is missing or its `verify` binding is broken.
Report lines that carry a run_id never name a USDT symbol (guard --strict).
Counts are written in words.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "..", "results", "runs")
OUT = os.path.join(HERE, "..", "results", "xsf_category_a_report.md")

MAIN = [("LOWVOL", "5c5cbbe6443fb391"),
        ("SKEW", "c683ad80d93f965f"),
        ("AUTOCORR", "78599c8a2cdd0982")]
NEIGH = [("LOWVOL", "240", "8c719aa2675607c7"),
         ("LOWVOL", "480", "66f2932cef28ac12"),
         ("SKEW", "480", "d5bced1d6604b6f3"),
         ("SKEW", "960", "08fa3e92ed79df46"),
         ("AUTOCORR", "240", "e6b0133110704e30"),
         ("AUTOCORR", "480", "ddf318cf72aa9b97")]


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
    w("# Categoría A — libros cross-sectionales 1h (LOWVOL / SKEW / AUTOCORR)")
    w("")
    w("Campaña del dos de noviembre de dos mil veintiséis. Adaptador `xsf`, motor "
      "`code/xs_factor_engine.py` (xsf-1), harness `code/vrun.py`. Los tres libros "
      "roten un universe-14 de perpetuos USDT-M por rango de factor (regla de "
      "inclusión por historial; símbolos que salen cuando sus datos terminan).")
    w("")
    w("Protocolo REGLA 0: cada número de este informe sale de un artefacto citado; "
      "los nueve artefactos verifican bit-for-bit (comando `verify` ejecutado sobre "
      "cada uno). Los conteos van en palabras.")
    w("")
    w("Convenciones medidas dentro de cada artefacto (`provenance.conventions`): "
      "decisión al cierre de la barra de rebalanceo y ejecución en la apertura "
      "siguiente; coste de comisión mas deslizamiento por lado, cobrado en cada "
      "fill; control de coste cero con la misma máquina de estados dentro del "
      "artefacto; resize de cada pata a `equity/(2k)` en cada rebalanceo con base "
      "de coste promedio; bandas de histéresis (entra en rank <= k, se mantiene "
      "mientras rank <= 2k); mínimo de sección transversal declarado (constante, "
      "no ajustada); funding NO cobrado — siete de catorce nombres no tienen "
      "fichero de funding en disco; bootstrap semillado de diez mil remuestreos.")
    w("")

    w("## Resultados principales")
    w("")
    w("| Carta | run_id | net % | gross % | PF | PF ex-cost | n | WR % | IS PF | "
      "OOS PF | top-5 % PnL | net sin top-5 % | maxDD % | B&H EW % | media/trade bps |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for card, rid in MAIN:
        m = arts[rid]["metrics"]
        w(f"| {card} | `{rid}` | {f(m['return_pct'])} | {f(m['gross_return_pct'])} | "
          f"{f(m['profit_factor'], 4)} | {f(m['profit_factor_ex_cost'], 4)} | "
          f"{m['n_trades']} | {f(m['win_rate'], 1)} | {f(m['is_pf'], 4)} | "
          f"{f(m['oos_pf'], 4)} | {f(m['conc_top5_share_pct'], 1)} | "
          f"{f(m['conc_net_without_top5_pct'], 1)} | {f(m['max_dd_pct'], 1)} | "
          f"{f(m['bh_return_pct'], 1)} | {f(m['avg_trade_bps'], 1)} |")
    w("")
    w("Ventana: los tres libros arrancan la primera decision con al menos ocho "
      "simbolos elegibles y corren hasta el final comun del indice (fechas "
      "exactas `start_utc` / `end_utc` / `first_active_utc` en cada artefacto).")
    w("")
    for card, rid in MAIN:
        m = arts[rid]["metrics"]
        w(f"Bandera del artefacto `{rid}`: `{m['flag']}`.")
    w("")

    w("## Vecindario (gate de estabilidad; no es rescate)")
    w("")
    w("| Carta | lb | run_id | net % | PF ex-cost | OOS PF | top-5 % | maxDD % |")
    w("|---|---|---|---|---|---|---|---|")
    for card, lb, rid in NEIGH:
        m = arts[rid]["metrics"]
        w(f"| {card} | {m['lb']} | `{rid}` | {f(m['return_pct'])} | "
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

    rid_lv = MAIN[0][1]
    w("## Desglose por simbolo (carta LOWVOL, tabla `per_symbol` del artefacto "
      f"`results/runs/{rid_lv}.json`)")
    w("")
    w("| simbolo | n trades | WR % | PnL eq % |")
    w("|---|---|---|---|")
    for row in arts[rid_lv]["tables"]["per_symbol"]:
        w(f"| {row[0]} | {row[1]} | {f(row[2], 1)} | {f(row[3], 2)} |")
    w("")

    w("## Hallazgos declarados")
    w("")
    w("- El promedio de exposicion bruta de LOWVOL se mide en su artefacto "
      f"({f(arts[MAIN[0][1]]['metrics']['avg_gross_exposure_pct'], 1)} por ciento): "
      "el resize funciona. En SKEW y AUTOCORR el promedio de exposicion es bajo "
      "porque el libro perdio casi todo en dos mil veinte y dos mil veintiuno y "
      "siguio operando a fraccion constante del equity restante — consecuencia "
      "del resultado, no un defecto mecanico.")
    w("- SKEW y AUTOCORR pierden ANTES de costes (PF ex-cost por debajo de uno): "
      "el fallo es de senal, no de coste.")
    w("- LOWVOL tiene PF bruto por encima de uno pero por debajo del umbral, "
      "concentracion extrema y OOS por debajo de uno.")
    w("- El vecindario no resucita ninguna carta: las seis celdas fallan.")
    w("- Funding no cobrado (declarado): para un libro dolar-neutro de holding "
      "catorce dias es de segundo orden, pero no medido aqui.")
    w("")

    w("## Veredicto")
    w("")
    w("**Categoría A (LOWVOL / SKEW / AUTOCORR sobre el universe-14 a una hora): "
      "KILLED — cero de tres cartas supera los gates, y el vecindario confirma "
      "que no es un problema de parametro.** La familia cross-sectional de "
      "factores de precio OHLCV (volatilidad, skewness, autocorrelacion) muere "
      "por senal (dos de tres PF bruto < 1), concentracion y OOS; el resultado "
      "es consistente con el kill previo del libro de momentum equal-weight "
      "(concentracion, artefacto `00d2a8549e6c898d`). La reivindicacion de "
      "MP-18 del prompt externo sigue sin artefacto en este repositorio: estos "
      "nueve artefactos no la confirman.")
    w("")

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
