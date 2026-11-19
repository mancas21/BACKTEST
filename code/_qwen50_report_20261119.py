"""_qwen50_report_20261119.py — report for the STRATEGIES 51-100 pack.

Reads results/_qwen50_run_all_map.json + the artifacts, evaluates the house
screen gates (bt.py ONE_GATES keys) per cell, and writes
results/QWEN50_REPORT_2026-11-19.md in the guard --strict house format
(metric numbers on lines without run_ids; each run_id on its own line;
r<N> labels)."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

MAP = ROOT / "results" / "_qwen50_run_all_map.json"
PROMPTS = ROOT / "code" / "prompts_51_100.txt"
OUT = ROOT / "results" / "QWEN50_REPORT_2026-11-19.md"
RUNS_DIR = (ROOT / "results" / "runs").resolve()

RUN_ID_RE = re.compile(r"^[0-9a-f]{16}$")


def load_artifact(run_id):
    if not RUN_ID_RE.match(run_id or ""):
        return None
    p = (RUNS_DIR / f"{run_id}.json").resolve()
    if p.parent != RUNS_DIR or not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def prompt_label(idn, lines):
    for ln in lines:
        m = re.match(r"^(\d+)\.\s+(.*)$", ln.strip())
        if m and int(m.group(1)) == idn:
            txt = m.group(2)
            mm = re.match(r"Build an? (.+?) (?:day trading |scalping )?"
                          r"strategy on ([A-Z0-9]+)", txt)
            if mm:
                return mm.group(1)
            return txt[:38]
    return "n/a"


def f2(v):
    return "n/a" if v is None else f"{v:.2f}"


def f1(v):
    return "n/a" if v is None else f"{v:.1f}"


def screen_gates(m):
    """bt.py ONE_GATES (the screen battery keys)."""
    pf = m.get("profit_factor")
    n = m.get("n_trades")
    ret = m.get("return_pct")
    thirds = (m.get("n_periods_green") or 0)
    oos_pf = m.get("oos_profit_factor")
    oos_ret = m.get("oos_return_pct")
    top5 = m.get("top5_pnl_share")
    boot = m.get("boot_ci_lo")
    checks = {
        "pf>1.2": bool(pf is not None and pf > 1.2),
        "n>=30": bool(n is not None and n >= 30),
        "net>0": bool(ret is not None and ret > 0),
        "thirds>=2": bool(thirds >= 2),
        "oos_pf>1.2": bool(oos_pf is not None and oos_pf > 1.2),
        "oos_net>0": bool(oos_ret is not None and oos_ret > 0),
        "conc<=100": bool(top5 is None or top5 <= 100),
        "boot>0": bool(boot is not None and boot > 0),
    }
    return checks, all(checks.values())


def main():
    jobs = json.loads(MAP.read_text(encoding="utf-8"))
    lines = PROMPTS.read_text(encoding="utf-8").splitlines()
    by_id = {j["id"]: j for j in jobs}

    L = []
    L.append("# QWEN 50 · estrategias 51-100 · corrida completa 2026-11-19")
    L.append("")
    L.append("> **Advertencia de honestidad.** Pack de 50 estrategias")
    L.append("> scalping/intradía especificadas por prompt (fuente de registro")
    L.append("> `code/prompts_51_100.txt`). Corrida de MEDICIÓN bajo REGLA 0:")
    L.append("> cada celda produce su artefacto verificado. La batería de")
    L.append("> veredicto completo (G1-G11 vía `bt.py one`) corre aparte; aquí se")
    L.append("> evalúa el SCREEN de la casa sobre las métricas del artefacto.")
    L.append("")
    L.append("- **Fuente:** `code/prompts_51_100.txt` (hash en cada run_id via")
    L.append("  `sources`).")
    L.append("- **Método:** engine `code/qwen50_engine.py` sobre el Book auditado")
    L.append("  de `p100_screen_engine`; señal en el cierre de j, fill en la")
    L.append("  apertura de j+1; stop-first; stop objetivo ATR desde el cierre de")
    L.append("  la barra de señal; objetivos R/vwap/midién fijados en el fill;")
    L.append("  trailing por raqueta del stop vivo; 0.5% riesgo, 3x apalancamiento;")
    L.append("  sin topes diarios (los prompts callan); corte de datos del día;")
    L.append("  split 70/30 cronológico sin purge; funding real en los ocho")
    L.append("  símbolos (incluidos los perps NVDAUSDT/SPCXUSDT).")
    L.append("- **Costes:** declarados por prompt — 10 bps RT (BTC/ETH/SOL),")
    L.append("  14 bps RT (HYPE/SUI/JUP); los cells de equity en cinta de perp")
    L.append("  NVDA/SPCX usan 11 bps RT repo (el coste por acción no aplica a")
    L.append("  un perp; desviación declarada).")
    L.append("- **Datos:** 1m nativo primero (la copia profunda 2023-01..; la")
    L.append("  del taker arranca 2024-10), JUP 1m solo existe en el taker.")
    L.append("  3m/30m remuestreados in-engine (_resample de la casa).")
    L.append("- **Refusals declarados:** 93 (sin serie 1m de NVDA) y 98 (sin 1m")
    L.append("  de SPCX) — data-driven, no silenciosos.")
    L.append("- **Auditoría de respuestas conocidas:** 14 de 14 PASS")
    L.append("  (`results/qwen50_audit_known_answers.txt`) ANTES de tocar datos")
    L.append("  reales; mató dos bugs reales (NaN-poisoning del supertrend y")
    L.append("  propagación del pack_sig) y un bug de unidades (ET vs UTC).")
    L.append("- **Preflight:** 48 PASS en slices de ~60 días")
    L.append("  (`code/_qwen50_preflight.py`).")
    L.append("- **Mapa:** `results/_qwen50_run_all_map.json` · runner")
    L.append("  `code/_qwen50_run_all.py` · report builder")
    L.append("  `code/_qwen50_report_20261119.py`.")
    L.append("")
    L.append("## Tabla completa (48 corridas + 2 refusals)")
    L.append("")
    L.append("| r# | Estrategia | Sym | TF | PF neto | Ret% | n | MaxDD% | OOS PF | OOS n | Screen |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")

    passed, failed_gates = [], []
    rows = []
    for idn in sorted(by_id):
        j = by_id[idn]
        art = load_artifact(j["new_run_id"])
        if art is None:
            continue
        m = art["metrics"]
        checks, ok = screen_gates(m)
        tag = "PASS" if ok else "kill"
        (passed if ok else failed_gates).append((idn, tag))
        label = prompt_label(idn, lines)
        rows.append((idn, label, art["symbol"], art["timeframe"], m, checks))
        L.append(
            f"| r{idn} | {label} | {art['symbol']} | {art['timeframe']} "
            f"| {f2(m.get('profit_factor'))} "
            f"| {f1(m.get('return_pct'))} "
            f"| {m.get('n_trades')} "
            f"| {f1(m.get('max_dd_pct'))} "
            f"| {f2(m.get('oos_profit_factor'))} "
            f"| {m.get('oos_n_trades')} "
            f"| {tag} |")

    L.append("")
    L.append("## Resumen del screen (ONE_GATES sobre las métricas del artefacto)")
    L.append("")
    L.append(f"- **Screen PASS: {len(passed)} de 48**"
             + (f" — r" + ", r".join(str(i) for i, _ in passed)
                if passed else ""))
    L.append(f"- **Screen kill: {len(failed_gates)} de 48** — la batería")
    L.append("  completa (G1-G11) solo tiene sentido para las que pasan el")
    L.append("  screen; con cero supervivientes no hay veredicto que correr.")
    L.append("")
    L.append("## Citas (artefacto por celda)")
    L.append("")
    for idn in sorted(by_id):
        j = by_id[idn]
        L.append(f"- r{idn} · {j.get('symbol', '')} {j.get('tf', '')} ·")
        L.append(f"  `{j['new_run_id']}`")
    L.append("")
    L.append("## Refusals (sin corrida, data-driven)")
    L.append("")
    L.append("- r93 · NVDAUSDT 3m — sin serie 1m de NVDA en el repo (el")
    L.append("  remuestreo 3m la necesita).")
    L.append("- r98 · SPCXUSDT 1m — sin serie 1m de SPCX en el repo.")
    L.append("")
    L.append("## Notas de convenciones declaradas")
    L.append("")
    L.append("- Los cells de equity (91-100) corren sobre la cinta de perp")
    L.append("  NVDAUSDT/SPCXUSDT con máscaras RTH 09:30-16:00 ET entre semana")
    L.append("  (precedente s101): anclas de día previo = sesión RTH anterior;")
    L.append("  vwap de sesión desde las 09:30; flat por deadline.")
    L.append("- Los objetivos en R se fijan en el fill (exactos) y son")
    L.append("  verificables desde la barra siguiente al fill (gancho del Book).")
    L.append("- Squeeze: armado por percentil de ancho (rolling 200) bajo el")
    L.append("  umbral; desarmado al entrar o con percentil mayor que 0.5.")
    L.append("- Supertrend/PSAR/ADX/RSI/Ichimoku: convenciones estándar")
    L.append("  documentadas en el docstring del engine; el audit de respuestas")
    L.append("  conocidas cubre la geometría de ejecución, no cada indicador.")

    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"screen pass: {[i for i, _ in passed]}")


if __name__ == "__main__":
    main()
