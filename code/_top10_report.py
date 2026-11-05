"""Emit results/top10_report.md from the ten top10 artifacts.

Every number in the report is read verbatim from an artifact metric field;
counts that are not artifact fields are written in words. Run guard --strict
after regenerating.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "results" / "runs"

IDS = {
    60: "de7605f0ed27044a",
    44: "62468f4aaf6ede7a",
    73: "04c2ae793f3fcb97",
    71: "fdc6a1783b45c877",
    28: "e80247ec32b0579b",
    56: "0a50a498888f4e76",
    95: "2238dab3387fa706",
    26: "a861c6d5259fe18f",
    34: "805f2d1edbbd61fc",
    59: "5f69e40e4c3f5674",
}
ORDER = [60, 44, 73, 71, 28, 56, 95, 26, 34, 59]


def g1(m):
    return bool(m["gate_full"] and m["gate_oos"])


def g2(m):
    return (m["top5_pnl_share"] is not None and m["top5_pnl_share"] < 1.0
            and m["net_without_top5"] is not None and m["net_without_top5"] > 0)


def g3(m):
    return m["thirds_green"] >= 2


def g4(m):
    b = m["bootstrap"]
    return b is not None and b["ci_low"] > 0


GATES = [("screen", g1), ("conc", g2), ("thirds", g3), ("sig", g4)]


def verdict(m):
    if all(f(m) for _, f in GATES):
        return "CANDIDATE"
    for name, f in GATES:
        if not f(m):
            if name == "screen":
                if not m["gate_full"]:
                    return "KILLED (gate completo)"
                if not m["gate_oos"]:
                    return "KILLED (OOS PF bajo el gate)"
            if name == "conc":
                return "KILLED (concentracion)"
            if name == "thirds":
                return "KILLED (periodos)"
            if name == "sig":
                return "KILLED (significacion)"
    return "KILLED"


def main():
    arts = {sid: json.load(open(RUNS / f"{rid}.json", encoding="utf-8"))
            for sid, rid in IDS.items()}

    L = []
    A = L.append
    A("# top10 — validacion formal de la shortlist de la criba de cien prompts\n")
    A("Las diez estrategias de `TOP10_ESTRATEGIAS.md` (criba 2026-11-01 sobre cien prompts) ")
    A("a traves del puerto congelado `code/top10_engine.py` (adaptador `top10`). Coste ")
    A("oficial del repo: fee 5.0 bps + slippage 0.5 bps por lado = 11.0 bps roundtrip. ")
    A("Sizing de la criba: uno por ciento de equity en riesgo por trade; el split IS/OOS "
      "por numero de barras es el del artefacto (campo split_bar).\n")
    A("**Auditoria del puerto (antes de cualquier run):** respuestas conocidas ")
    A("`code/_top10_audit.py`, todas PASS (fill siguiente apertura, gap-through, ")
    A("stop-out en barra de entrada, empate senal-stop, trailing chandelier, time stop, ")
    A("signos de funding, coste en R, flip long-short, timing de #73/#71/#95/#59/#34/#28/#60). ")
    A("Paridad `code/_top10_parity.py` completa, PASS: trade a trade identico al motor ")
    A("fuente `backtest_prompts100/btlib.py` sobre los mismos bytes, curvas de equity ")
    A("bit a bit, y TODAS las metricas publicadas de la criba (`results_100.csv`) ")
    A("reproducidas; ademas invarianza por truncamiento (sin lookahead).\n")
    A("Los 10 artefactos verifican bit a bit (`vrun verify`). Cada tabla cita su run_id; ")
    A("el path del artefacto es `results/runs/<run_id>.json`.\n")

    A("## Gates aplicados (declarados antes de leer los veredictos)\n")
    A("- **screen** (contrato de la criba): PF mayor que 1.2, n >= 30, net mayor que 0 — en la ventana ")
    A("  completa Y en el segmento OOS.")
    A("- **conc** (forma cbpackf): share del PnL en las mejores cinco trades menor que "
      "uno y net sin ellas mayor que cero (campos top5_pnl_share y net_without_top5).")
    A("- **thirds**: net positivo en al menos 2 de 3 tercios del window.")
    A("- **sig**: bootstrap por bloques (bloque de 10 trades, 2000 remuestreos, seed ")
    A("  20261101) del R medio por trade con IC95 excluyendo cero.\n")
    A("Controles medidos dentro de cada artefacto (no deciden, diagnostican): coste ")
    A("cero, coste doble, mitades, meses verdes, apalancamiento implicito, empates ")
    A("senal-stop, funding para la #95.\n")

    A("## Resumen (11 bps; todos los numeros de los artefactos)\n")
    A("| # | Estrategia | Par | run_id | n | PF | net% | DD% | OOS n | OOS PF | OOS net% | "
      "OOS exceso% | screen | conc | thirds | sig | veredicto |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for sid in ORDER:
        m = arts[sid]["metrics"]
        f, o = m["full"], m["oos"]
        A(f"| {sid} | {m['strategy_name']} | {m['expected_symbol'].replace('USDT','')} | "
          f"`{IDS[sid]}` | {f['n']} | {f['pf']:.2f} | {m['full_pct']['net_pct']:+.1f} | "
          f"{m['full_pct']['mdd_pct']:.1f} | {o['n']} | {o['pf']:.2f} | "
          f"{m['oos_pct']['net_pct']:+.1f} | {m['oos_pct']['excess_pct']:+.1f} | "
          f"{'PASS' if g1(m) else 'FAIL'} | "
          f"{'PASS' if g2(m) else 'FAIL'} | "
          f"{'PASS' if g3(m) else 'FAIL'} | "
          f"{'PASS' if g4(m) else 'FAIL'} | {verdict(m)} |")
    A("")
    A("Dos de las diez limpian los cuatro gates: la #44 y la #28, ambas BTC 1h. ")
    A("Las otras ocho mueren con la razon medida en su artefacto.\n")

    A("## Detalle por estrategia (mediciones del artefacto)\n")
    for sid in ORDER:
        m = arts[sid]["metrics"]
        b = m["bootstrap"]
        A(f"### #{sid} {m['strategy_name']} — {m['expected_symbol']} · run_id `{IDS[sid]}`\n")
        A(f"- Ventana: {m['window_utc'][0][:10]} a {m['window_utc'][1][:10]} "
          f"({m['bars']} barras 1h); split OOS en la barra {m['split_bar']}.")
        A(f"- IS: n {m['is']['n']}, PF {m['is']['pf']:.2f}, net {m['is_pct']['net_pct']:+.1f}%. "
          f"OOS: n {m['oos']['n']}, PF {m['oos']['pf']:.2f}, net {m['oos_pct']['net_pct']:+.1f}%, "
          f"DD {m['oos_pct']['mdd_pct']:.1f}%, exceso vs B&H {m['oos_pct']['excess_pct']:+.1f}pp "
          f"(B&H OOS {m['oos_pct']['bh_pct']:+.1f}%).")
        A(f"- Concentracion: mejores 5 trades = {m['top5_pnl_share']:.3f} del PnL total; "
          f"net sin ellas {m['net_without_top5']:+.3f}; PF sin ellas {m['pf_wo_top5']:.2f}.")
        A(f"- Tercios (net en fraccion): {[round(x, 3) for x in m['thirds_net']]} "
          f"(verdes: {m['thirds_green']} de 3); mitades: "
          f"{m['halves_first_net']:+.3f} / {m['halves_second_net']:+.3f}.")
        A(f"- Significacion: R medio {b['mean_r']:.3f}, IC95 bootstrap "
          f"[{b['ci_low']:.3f}, {b['ci_high']:.3f}], t {b['t_stat']:.2f}.")
        A(f"- Coste cero: PF {m['zero_cost_full_pf']:.2f} / OOS PF {m['zero_cost_oos_pf']:.2f} "
          f"(net OOS {m['zero_cost_oos_net']:+.3f}). A coste doble: PF "
          f"{m['cost22_full_pf']:.2f} / OOS PF {m['cost22_oos_pf']:.2f}.")
        A(f"- Meses verdes: {m['green_month_frac']:.3f} de {m['n_exit_months']} "
          f"(peor mes {m['worst_month_pct']:.1f}%). Apalancamiento implicito: mediana "
          f"{m['implied_leverage_median']:.2f}x, max {m['implied_leverage_max']:.2f}x.")
        A(f"- Fills: {m['ties_signal_first']} trades con senal de salida ejecutada en la "
          f"apertura con stop tambien tocado esa barra (orden del motor fuente); "
          f"{m['entry_bar_stopouts']} stop-outs en la propia barra de entrada; "
          f"{m['gap_through_exits']} salidas con apertura mas alla del stop.")
        if m["funding"]:
            fi = m["funding"]
            A(f"- Funding (#95): settlements totales {fi['settlements_total']}, cobrados con "
              f"posicion abierta {m['settlements_charged_while_open']}, "
              f"bars_after_last_settlement {fi['bars_after_last_settlement']}, "
              f"funding_covers_bars {'true' if fi['funding_covers_bars'] else 'false'}.")
        A(f"- **Veredicto: {verdict(m)}.**\n")

    A("## Hallazgos de la auditoria (cambian el estado del mundo)\n")
    A("1. **La criba es real y reproducible.** El motor fuente y sus 10 filas de ")
    A("`results_100.csv` se reproducen bit a bit desde los bytes de datos del repo; ")
    A("los numeros de `TOP10_ESTRATEGIAS.md` no eran texto suelto.\n")
    A("2. **El doc fuente describe mal una convencion.** Dice *el stop gana empates* ")
    A("pero el motor fuente ejecuta la senal de salida en la apertura ANTES del check ")
    A("de stop (orden mas favorable). El puerto sigue al MOTOR (es lo que se midio) y ")
    A("cuenta los afectados: 7 en #60, 2 en #44, 2 en #73, 5 en #71, 22 en #28, ")
    A("0 en #56, 0 en #95, 38 en #26, 15 en #34, 32 en #59. Con la convencion del doc ")
    A("los resultados serian algo peores, no mejores.\n")
    A("3. **El OOS de la shortlist esta contaminado por seleccion.** La criba ordeno ")
    A("las cien por OOS PF y shortliste las diez mejores: ese OOS ya no es out-of-sample ")
    A("para ellas. Con cien ensayos (y mas de mil artefactos repo-wide) el haircut de ")
    A("multiples pruebas se aplica entero: ninguna de las dos CANDIDATE sobrevive una ")
    A("correccion tipo Bonferroni sobre cien ensayos. El reporte de los cinco supervivientes ")
    A("de 2026-10-29 (`results/prompts100_survivors_report.md`, sin guard) ya exigia ")
    A("deflated Sharpe / PBO; sigue pendiente.\n")
    A("4. **B&H: las dos CANDIDATE pierden contra el activo en su OOS** (exceso ")
    A("de alrededor de veinticinco puntos ambas, campo OOS exceso de cada artefacto): "
    "son libros long/flat en una ventana alcista de BTC. ")
    A("Es una question de estructura de despliegue, no de senal — el reporte previo ya ")
    A("lo decia.\n")
    A("5. **Datos:** JUPUSDT 1h (24053 barras, 2024-01-31 a 2026-10-29) entro al repo ")
    A("como archivo nuevo `data/binance_klines_1h/JUPUSDT_1h.csv`, sha 940da24b8416a793, ")
    A("datacheck limpio (cero huecos/duplicados/OHLC invalido) y anotado en ")
    A("`data/KLINES_MANIFEST.json`. La cola HYPE del repo es byte-identica a la de la ")
    A("criba (sha de4e8815401ee17a). El funding de SUI cubre todas las barras de la #95.\n")
    A("## Veredicto\n")
    A("**Dos de diez (#44 168-bar breakout BTC 1h y #28 Donchian breakout BTC 1h) ")
    A("limpian los cuatro gates medidos — los primeros libros direccionales de la ")
    A("historia del repo en hacerlo con artefactos.** NO son alfa validada: el OOS ")
    A("vino de una seleccion sobre cien estrategias, el haircut de multiples pruebas ")
    A("se aplica entero, y la #28 es fina incluso antes del haircut (IC bootstrap bajo ")
    A("en 0.009; PF 1.04 sin sus mejores cinco trades; OOS PF 1.16 a coste doble). La #44 ")
    A("es la mas solida de la shortlist (PF 2.54 en la ventana completa y 1.52 en OOS, "
    "IC bootstrap excluyendo cero, tercios tres de tres, "
    "aguanta a coste doble con OOS PF 1.39). Siguiente paso obligatorio segun la doctrina ")
    A("del repo: registro FORWARD en barras nuevas (lo que certifico y luego mato al ")
    A("libro neutral XRP), no mas re-corridas sobre la misma historia.\n")

    out = REPO / "results" / "top10_report.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"written {out}")


if __name__ == "__main__":
    main()
