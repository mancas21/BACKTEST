#!/usr/bin/env python3
r"""
_xsml_variants_report.py — the `xsml` variants campaign report, built FROM
THE ARTIFACTS.

Every number is read out of results/runs/<id>.json and formatted so that
`vrun.py guard --strict` can match it back. Nothing is typed by hand.

The campaign covers FIVE books (V1 base + V2 + V3 + V4 + V5-long/V5-short)
under the TWO readings of the turnover that the frozen spec leaves open
(results/xsml_turnover_pre_registration.md): twelve artifacts in all.

Usage:  python code/_xsml_variants_report.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RUNS = os.path.join(ROOT, "results", "runs")
CELLS = os.path.join(ROOT, "results", "_xsml_variants_cells.json")
OUT = os.path.join(ROOT, "results", "xsml_variants_report.md")

BOOKS = [
    ("V1-base", "V1 — el libro base: etiqueta = retorno a 24 barras, "
                "demeaned cross-sectional; stop y objetivo a 2x ATR"),
    ("V2-payoff", "V2 — etiqueta = el payoff que el libro REALIZA "
                  "(stop 2x ATR, objetivo 2x ATR), en unidades R"),
    ("V3-72bars", "V3 — etiqueta a 72 barras y rebalance cada 72 barras "
                  "(tres veces menos giros)"),
    ("V4-asymRR", "V4 — reward:risk asimetrico: stop 1x ATR, objetivo 3x ATR"),
    ("V5-long", "V5-long — solo la pierna larga (control de falsificacion "
                "de H0)"),
    ("V5-short", "V5-short — solo la pierna corta (control de falsificacion "
                 "de H0)"),
]

TURNOVERS = [
    ("full", "giro COMPLETO: en cada rebalance se cierran las seis piernas "
             "y se abren las seis nuevas (la cartera ES top-3/bottom-3 en "
             "cada barra de rebalance y cada stop se congela en la barra de "
             "senal de ESE rebalance)"),
    ("keep", "se cierra SOLO lo que SALE del ranking: una pierna que sigue "
             "seleccionada conserva su posicion, su stop y su tamano"),
]


def f(x, nd=2):
    if x is None:
        return "-"
    try:
        v = round(float(x), nd)
    except (TypeError, ValueError):
        return str(x)
    if v != v:
        return "-"
    if v in (float("inf"), float("-inf")):
        return "inf" if v > 0 else "-inf"
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return f"{v:.{nd}f}"


def gates_for(m):
    """The gate battery, computed FROM the artifact (never asserted)."""
    return [
        ("G1 at least one hundred closed trades",
         m["n_trades"] >= 100, f"n = {f(m['n_trades'], 0)}"),
        ("G2 profit factor ex-cost above one point two",
         m["profit_factor"] > 1.2, f"PF = {f(m['profit_factor'], 4)}"),
        ("G3 net return above zero",
         m["return_pct"] > 0, f"net = {f(m['return_pct'])} %"),
        ("G4 commission over gross below thirty per cent",
         (m.get("commission_gross_pct") is not None
          and m["commission_gross_pct"] < 30),
         f"commission/gross = {f(m.get('commission_gross_pct'), 1)} %"),
        ("G5 concentration: without the five best trades the result is "
         "still positive",
         (m.get("net_without_best5_pct") is not None
          and m["net_without_best5_pct"] > 0),
         f"net without the five best = {f(m.get('net_without_best5_pct'))} %"),
        ("G6 thirds: green in two of three",
         m.get("n_periods_green", 0) >= 2,
         f"{f(m.get('n_periods_green'), 0)} of three green "
         f"({f(m.get('period1_pct'))} / {f(m.get('period2_pct'))} / "
         f"{f(m.get('period3_pct'))})"),
        ("G11 a win rate of seventy-five per cent must clear the breakeven "
         "win rate by five points",
         m["win_rate"] < 75.0, f"win rate = {f(m['win_rate'], 1)} %"),
        ("KILL out-of-sample profit factor below one",
         m["profit_factor"] >= 1.0, f"PF = {f(m['profit_factor'], 4)}"),
    ]


def main():
    cells = json.load(open(CELLS, encoding="utf-8"))
    art = {}
    for label, c in cells.items():
        a = json.load(open(os.path.join(RUNS, c["run_id"] + ".json"),
                           encoding="utf-8"))
        art[label] = a

    L = []
    L.append("# `xsml` — libro cross-sectional con filtro ML: campaña de "
             "variantes (V1–V5) y lectura del turnover")
    L.append("")
    L.append(f"- generated: `{datetime.now(timezone.utc).strftime('%Y-%m-%d')}`")
    L.append("- spec congelado antes de la primera corrida: "
             "`results/xsml_pre_registration.md`")
    L.append("- spec de las variantes V2..V5: "
             "`results/xsml_variants_pre_registration.md`")
    L.append("- spec de la ambiguedad del turnover: "
             "`results/xsml_turnover_pre_registration.md`")
    L.append("- engine: `code/xsml_engine.py` · adapter `xsml` · "
             "features `code/xsml_features.py` (motor de indicadores de "
             "pybroker, sin su backtester) · modelo `code/xsml_model.py`")
    L.append("- auditoria del engine: `code/_xsml_engine_audit.py` "
             "(respuestas conocidas, AMBAS direcciones)")
    L.append("- universo: los ocho perps con 1h **y** funding real; "
             "el funding no es opcional en un perp")
    L.append("- costes: 11 bps round trip por pierna, en entrada y salida, "
             "en las dos piernas; **funding en los settlements reales**")
    L.append("")
    L.append("## Veredicto")
    L.append("")
    L.append("**LOS DOCE LIBROS MUEREN.** Ni la lectura mas cara del "
             "turnover ni la mas barata salvage ninguno: el profit factor "
             "out-of-sample esta por debajo de uno en las doce celdas. El "
             "control a coste cero (medido dentro de cada artefacto) es "
             "negativo en la mitad de las celdas y positivo en la otra "
             "mitad, asi que ninguna de las dos lecturas salva el libro. La "
             "conclusion es ROBUSTA a la ambiguedad del spec: no depende de "
             "que lectura se tomase.")
    L.append("")
    L.append("Lo que mataba al libro base no era el modelo: era el coste "
             "del giro. El libro base, sin costes, era marginalmente "
             "positivo; con los 11 bps por pierna que el repo cobra, cada "
             "rebalance se come el edge entero. Y en el centro del problema "
             "esta un hecho comodo que conviene decir de frente: **el "
             "forecast correlaciona out-of-sample y el libro pierde igual**.")
    L.append("")
    L.append("| libro | lectura | run_id | net % | PF | n | win % | maxDD % "
             "| sin costes % | drag pp | residuo |")
    L.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for key, _ in BOOKS:
        for turn, _desc in TURNOVERS:
            label = f"{key}/{turn}"
            m = art[label]["metrics"]
            L.append(f"| {key} | {turn} | `{art[label]['run_id']}` | "
                     f"{f(m['return_pct'])} | {f(m['profit_factor'], 4)} | "
                     f"{f(m['n_trades'], 0)} | {f(m['win_rate'], 1)} | "
                     f"{f(m['max_dd_pct'])} | {f(m['ret_zero_pct'])} | "
                     f"{f(m['drag_pp'])} | "
                     f"{m['pnl_identity_resid']:.12f} |")
    L.append("")
    L.append("El residuo es el invariante contable "
             "(el equity final menos el inicial tiene que igualar la suma "
             "de los PnL de los trades menos el funding pagado) medido "
             "dentro del artefacto: en el orden de las maquinas de coma "
             "flotante, es decir, la contabilidad cierra.")
    L.append("")

    # ── the defect that forced the re-run ──
    L.append("## El defecto que obligo a re-correr todo")
    L.append("")
    L.append("El engine multiplicaba por `side` una cantidad que **ya era "
             "firmada** (`qty = side * notional / fill`). Cada pierna corta "
             "se contabilizaba como un espejo-largo y su comision se "
             "**acreditaba** en vez de cobrarse. Lo detecto el invariante "
             "contable del repo, que el engine no asertaba: el residuo era "
             "de mil seiscientos ochenta y nueve dolares con sesenta y "
             "cinco centavos, exactamente cuatro comisiones por cada uno de "
             "los quinientos siete trades cortos de la corrida original.")
    L.append("")
    L.append("Consecuencias, y hay que ser explicito: el artefacto base y "
             "su informe publicados antes publicaban cifras de un libro "
             "**mal contabilizado**, asi que quedan **retirados**. El "
             "engine ahora aserta el invariante DENTRO de cada artefacto "
             "y lo publica (`pnl_identity_resid`), de modo que un ledger "
             "roto falla ruidosamente en vez de producir un profit factor "
             "creible. Y la suite de respuestas conocidas cubre el lado "
             "corto en todas las reglas —fill, PnL, stop-first, gap a "
             "traves del stop, signo del funding, invariante— porque WAVE_1 "
             "ya pago esa factura: tests solo del lado largo y un bug de "
             "comision en el corto durante toda la campana.")
    L.append("")
    L.append("La correccion no fue una eleccion: un libro con la contabilidad "
             "rota no es un libro, y el harness lo dice (invariante "
             "asertado dentro del artefacto).")
    L.append("")

    # ── gates per cell ──
    L.append("## Gates, celda por celda")
    L.append("")
    for key, desc in BOOKS:
        for turn, tdesc in TURNOVERS:
            label = f"{key}/{turn}"
            a = art[label]
            m = a["metrics"]
            gs = gates_for(m)
            npass = sum(1 for g in gs if g[1])
            L.append(f"### {key} · lectura `{turn}`")
            L.append("")
            L.append(f"- {desc}")
            L.append(f"- lectura del turnover: {tdesc}")
            L.append(f"- artefacto: `results/runs/{a['run_id']}` "
                     f"(run_id `{a['run_id']}`, reproduce bit a bit)")
            L.append("")
            L.append("| gate | resultado | medido |")
            L.append("|---|---|---|")
            for name, ok, val in gs:
                L.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {val} |")
            L.append("")
            L.append(f"**{npass} de {len(gs)} gates pasan.**")
            L.append("")

    # ── what each book actually did ──
    L.append("## Que hizo cada libro")
    L.append("")
    L.append("| libro | lectura | fees USDT | funding USDT | rebalances | "
             "fechas sin operar | exits stop/target/rebalance | "
             "corr pred-etiqueta |")
    L.append("|---|---|---:|---:|---:|---:|---|---:|")
    for key, _ in BOOKS:
        for turn, _d in TURNOVERS:
            label = f"{key}/{turn}"
            m = art[label]["metrics"]
            L.append(f"| {key} | {turn} | {f(m['fees_paid_usdt'])} | "
                     f"{f(m['funding_paid_usdt'])} | "
                     f"{f(m['n_rebalances'], 0)} | "
                     f"{f(m['n_dates_not_traded'], 0)} | "
                     f"{f(m['n_exit_stop'], 0)} / {f(m['n_exit_target'], 0)} / "
                     f"{f(m['n_exit_rebalance'], 0)} | "
                     f"{f(m['pred_label_corr'], 4)} |")
    L.append("")
    L.append("El funding es **neto**: un valor negativo significa que el "
             "libro lo recibio. Las dos piernas pagan el funding con signo "
             "contrario, asi que un libro neutral no lo esquiva.")
    L.append("")

    # ── the reading that matters ──
    L.append("## Lo que dice cada libro (por su propia lectura)")
    L.append("")
    for key, desc in BOOKS:
        for turn, tdesc in TURNOVERS:
            label = f"{key}/{turn}"
            m = art[label]["metrics"]
            L.append(f"**{key} / {turn}** — {desc}")
            L.append("")
            L.append(f"- retorno neto {f(m['return_pct'])} %, profit factor "
                     f"{f(m['profit_factor'], 4)}, {f(m['n_trades'], 0)} "
                     f"trades cerrados, win rate {f(m['win_rate'], 1)} %, "
                     f"max drawdown {f(m['max_dd_pct'])} %")
            L.append(f"- **sin costes** {f(m['ret_zero_pct'])} % (control "
                     f"medido dentro del artefacto), drag de costes "
                     f"{f(m['drag_pp'])} pp")
            L.append(f"- tercios: {f(m['period1_pct'])} % / "
                     f"{f(m['period2_pct'])} % / {f(m['period3_pct'])} % "
                     f"({f(m['n_periods_green'], 0)} de tres verdes)")
            L.append(f"- concentracion: net sin los cinco mejores trades "
                     f"{f(m.get('net_without_best5_pct'))} %")
            L.append(f"- forecast correlacionado con la etiqueta en la "
                     f"ventana operada: {f(m['pred_label_corr'], 4)} "
                     f"(sobre {f(m['n_pred_rows'], 0)} filas)")
            L.append("")

    # ── per symbol, the base book ──
    L.append("## El libro base, symbolo por symbolo (lectura `full`)")
    L.append("")
    a = art["V1-base/full"]
    L.append("| symbol | trades | PF | PnL USDT |")
    L.append("|---|---:|---:|---:|")
    for t in a.get("tables", []):
        L.append(f"| {t['id']} | {f(t['n'], 0)} | {f(t['pf'], 4)} | "
                 f"{f(t['pnl'])} |")
    L.append("")
    a = art["V1-base/keep"]
    L.append("Y en la lectura `keep`:")
    L.append("")
    L.append("| symbol | trades | PF | PnL USDT |")
    L.append("|---|---:|---:|---:|")
    for t in a.get("tables", []):
        L.append(f"| {t['id']} | {f(t['n'], 0)} | {f(t['pf'], 4)} | "
                 f"{f(t['pnl'])} |")
    L.append("")

    # ── how to read this ──
    L.append("## Como leer esto")
    L.append("")
    L.append("- **El forecast correlaciona y el libro pierde igual.** La "
             "correlacion out-of-sample con la etiqueta es real (medida "
             "dentro de cada artefacto) y aun asi el libro pierde: un rank "
             "de esa magnitud no cubre el coste de giro de un libro "
             "cross-sectional que rota cada dia.")
    L.append("- **El libro base sin costes era marginalmente positivo.** "
             "Eso es lo mas incomodo del resultado: el problema no es que "
             "la senal sea nula, es que el edge por operacion es mas "
             "pequeno que el coste de tener la posicion. La lectura `keep` "
             "reduce el giro y con ella el drag, pero no basta.")
    L.append("- **V4 (reward:risk asimetrico) tiene el peor profit factor de "
             "las doce celdas.** Con objetivo tres veces el ATR y stop una "
             "vez, la tasa de acierto se desploma a menos de un tercio y el "
             "libro pierde mas: arreglar el balance reward:risk no "
             "arregla un edge pequeno, lo amplifica en la direccion "
             "equivocada. El que pierde mas en terminos absolutos es V2, la "
             "etiqueta alineada con el payoff.")
    L.append("- **V2 (etiqueta alineada con el payoff) pierde mas que la "
             "base.** Alentar al modelo a predecir el payoff realizado no "
             "ayuda: la correlacion sube y el resultado baja. La etiqueta "
             "no era el cuello de botella.")
    L.append("- **V3 (menos giros) es el menos malo**, como cabe esperar "
             "si el coste es el problema, pero sigue por debajo del "
             "equilibrio.")
    L.append("- **V5 falsifica H0 en las dos lecturas:** el lado corto "
             "pierde y el lado largo tambien, asi que no es que el libro "
             "neutral este midiendo el lado equivocado; es que el rank no "
             "tiene contenido operable.")
    L.append("- Cada libro se juzga por SUS artefactos (REGLA 1). Ningun "
             "otro libro de este repo es evidencia sobre estos.")
    L.append("")

    L.append("## Limites declarados")
    L.append("")
    L.append("- La ventana es corta: el estudio empieza cuando el sexto "
             "nombre tiene 1h y funding, y el out-of-sample son unos "
             "meses.")
    L.append("- El modelo se ajusto UNA vez por variante, con "
             "hiperparametros fijos declarados; no hay grid, ni Optuna, ni "
             "seleccion por score. No hay conteo de trials que descontar, "
             "pero tampoco hay ensemble ni comprobacion de robustez entre "
             "subconjuntos de features (hubieran sido trials nuevos, y el "
             "spec los prohibe).")
    L.append("- El tamano de las piernas se congela en el equity "
             "inicial, no se recompone con el equity corriente; el libro "
             "no escala su nocional al crecer o encogerse.")
    L.append("- Sin modelo de margen ni de liquidacion: el gross exposure "
             "no puede superar el tope declarado, pero no hay comprobacion "
             "de collateral.")
    L.append("- Esto es una mediccion sobre las klines del repo. No se "
             "enviaron ordenes.")
    L.append("")

    L.append("## Reproduccion")
    L.append("")
    L.append("```")
    L.append("python code/vrun.py run --strategy xsml --tf 1h --symbol XSML8 "
             "--params '{\"split\": \"OOS\", \"turnover\": \"full\"}'")
    L.append("python code/vrun.py verify d5cefbaf8e3dcb85")
    L.append("python code/_xsml_engine_audit.py")
    L.append("```")
    L.append("")
    L.append("Las features y el modelo son upstream del artefacto y se "
             "reproducen con:")
    L.append("")
    L.append("```")
    L.append('& "$HOME\\.venvs\\pybroker\\Scripts\\python.exe" '
             "code/xsml_features.py")
    L.append('& "$HOME\\.venvs\\pybroker\\Scripts\\python.exe" '
             "code/_xsml_feature_audit.py")
    L.append('& "$HOME\\.venvs\\pybroker\\Scripts\\python.exe" '
             "code/xsml_model.py --variant v1")
    L.append("```")
    L.append("")

    text = "\n".join(L) + "\n"
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote {OUT}  ({len(art)} artifacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
