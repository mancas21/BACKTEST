"""_top100_bundle.py — package the refreshed top-100 backtest for delivery:

  artifacts/<run_id>.json   every cited artifact (one per unique run_id)
  code/                     the exact engine files recorded in each artifact's
                            provenance.engine_files, plus vrun.py and the
                            _top100_* tooling
  reports/                  the ranking CSV (both variants) + MD report
  MANIFEST.json             per-row: rank, run_id, cmd (verbatim re-run cmd),
                            engines, data inputs with sha256
  README.md                 what this is + how to verify
Zips the staging tree to Downloads/top100_backtest_pack_2026-10-31.zip.
"""

import csv
import hashlib
import json
import os
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
DL = os.path.join(os.path.expanduser("~"), "Downloads")
NAME = "top100_backtest_pack_2026-10-31"
ZIP = os.path.join(DL, NAME + ".zip")

rows = list(csv.DictReader(
    open(os.path.join(ROOT, "results", "top100_ranking_refresh_2026-10-31.csv"),
         encoding="utf-8-sig")))

run_ids = []
for r in rows:
    if r["run_id"] not in run_ids:
        run_ids.append(r["run_id"])

stage = os.path.join(os.path.expandvars("%TEMP%"), NAME)
if os.path.exists(stage):
    shutil.rmtree(stage)
for sub in ("artifacts", "code", "reports"):
    os.makedirs(os.path.join(stage, sub))

engines, manifest, data_files = set(), [], {}
for rank, r in enumerate(rows, 1):
    rid = r["run_id"]
    d = json.load(open(os.path.join(ROOT, "results", "runs", rid + ".json")))
    shutil.copy2(os.path.join(ROOT, "results", "runs", rid + ".json"),
                 os.path.join(stage, "artifacts", rid + ".json"))
    ef = (d.get("provenance") or {}).get("engine_files") or []
    engines.update(ef)
    inputs = []
    for i in (d.get("inputs") or []):
        if isinstance(i, dict) and i.get("path"):
            rel = os.path.relpath(i["path"], ROOT).replace("\\", "/")
            inputs.append({"path": rel, "sha256": i.get("sha256"), "bars": i.get("bars")})
            data_files[rel] = i.get("sha256")
        elif isinstance(i, (list, tuple)) and len(i) >= 2:
            rel = os.path.relpath(i[0], ROOT).replace("\\", "/")
            inputs.append({"path": rel, "sha256": i[1]})
            data_files[rel] = i[1]
    manifest.append({
        "rank": rank, "run_id": rid,
        "estrategia": r["estrategia"], "que_hace": r["que_hace"],
        "pack": r["pack"], "veredicto_pack": r["veredicto_pack"],
        "simbolo": r["simbolo"], "tf": r["tf"],
        "ret_neto_pct": r["ret_neto_pct"], "profit_factor": r["profit_factor"],
        "n_ops": r["n_ops"], "verificacion": r["verificacion"],
        "cmd": d.get("cmd"),
        "engine_files": sorted(ef),
        "engine_sha256": (d.get("provenance") or {}).get("engine_sha256"),
        "inputs": inputs,
    })

missing = []
VRUN = open(os.path.join(ROOT, "code", "vrun.py"), encoding="utf-8").read()
for ef in sorted(engines):
    src = os.path.join(ROOT, "code", ef)
    if not os.path.exists(src):
        # subdirectory engines: resolve through vrun's own ADAPTERS sources,
        # e.g. mpv3 -> code/claude_mp20_v3/strategies.py
        hit = None
        for m in __import__("re").finditer(
                r"os\.path\.join\(CODE,\s*\"([^\"]+)\",\s*\"([^\"]+)\"\)", VRUN):
            if m.group(2) == ef:
                cand = os.path.join(ROOT, "code", m.group(1), m.group(2))
                if os.path.exists(cand):
                    hit = cand
                    break
        if hit:
            src = hit
        else:
            missing.append(ef)
            continue
    shutil.copy2(src, os.path.join(stage, "code", ef))
for tool in ("vrun.py", "_top100_rank.py", "_top100_refresh.py", "_top100_rerun.py",
             "_top100_report.py", "_top100_bundle.py"):
    shutil.copy2(os.path.join(ROOT, "code", tool), os.path.join(stage, "code", tool))
for rep in ("top100_ranking_refresh_2026-10-31.csv",
            "top100_ranking_refresh_2026-10-31_es_excel.csv",
            "top100_ranking_refresh_2026-10-31.md"):
    shutil.copy2(os.path.join(ROOT, "results", rep), os.path.join(stage, "reports", rep))

json.dump({"pack": NAME, "rows": len(rows), "artifacts": len(run_ids),
           "engine_files": sorted(engines), "missing_engines": missing,
           "data_inputs": data_files, "strategies": manifest},
          open(os.path.join(stage, "MANIFEST.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)

readme = f"""# Top-100 backtest pack — 2026-10-31

Contenido y procedencia:

- `artifacts/` — los artefactos citados por el ranking refrescado
  (`results/top100_ranking_refresh_2026-10-31.csv`), uno por run_id unico.
  Cada JSON lleva su cmd original, provenance (sha256 del engine y del
  harness), metricas y tablas. Son la fuente de verdad de cada numero.
- `code/` — los engine files EXACTOS grabados en `provenance.engine_files`
  de cada artefacto, mas el harness `code/vrun.py` y el tooling `_top100_*`.
  Copiarlos a un repo con la misma estructura (`code/`, `data/`, `results/runs/`).
- `reports/` — el ranking completo (CSV coma estandar, CSV punto-y-coma para
  Excel espanol, y el informe markdown con guard OK).
- `MANIFEST.json` — por estrategia: rank, run_id, comando verbatim para
  re-ejecutarla, engines que la producen y los ficheros de datos que hash-ea
  cada artefacto (ruta + sha256 + barras).

Como reproducir cualquier fila (desde la raiz del repo, con los mismos datos):

    python code/vrun.py render <run_id>     # numeros SOLO desde el artefacto
    python code/vrun.py verify <run_id>     # re-ejecuta; exige bit-for-bit
    python code/vrun.py pverify --ids <id1,id2,...> --workers 8

Estado de verificacion de este pack: todos los artefactos incluidos salieron
OK en pverify el 2026-10-31 sobre los datos actuales del repo.

ADVERTENCIA (repositorio de origen): el ranking es DESCRIPTIVO por retorno
neto medido, NO una validacion. El unico conjunto que pasa todos los gates
es la rejilla delta-neutral XRP; el resto proviene en su mayoria de packs
KILLED y el veredicto de cada pack viaja en la columna veredicto_pack.

Datos: NO incluidos (los CSV de klines/funding pesan gigas). Las rutas y
sha256 de cada fichero de datos estan en MANIFEST.json (campo data_inputs /
inputs), de modo que cualquiera puede comprobar que sus datos son los mismos
bytes que produjeron estos numeros.
"""
open(os.path.join(stage, "README.md"), "w", encoding="utf-8").write(readme)

if os.path.exists(ZIP):
    os.remove(ZIP)
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for base, _, files in os.walk(stage):
        for fn in sorted(files):
            p = os.path.join(base, fn)
            z.write(p, os.path.join(NAME, os.path.relpath(p, stage)))
shutil.rmtree(stage)

n_files = sum(1 for _ in zipfile.ZipFile(ZIP).namelist())
print(f"zip -> {ZIP}")
print(f"rows={len(rows)} artifacts={len(run_ids)} engine_files={len(engines)} "
      f"missing={missing} zip_files={n_files} size={os.path.getsize(ZIP)/1e6:.2f}MB")
