#!/usr/bin/env python
"""Build a machine-readable index for the top-100 report.

Reads results/_top100_2026_11_09_rank.json and, for each ranked book, the cited
artifact. Emits results/top100_2026-11-09_strategies.json with the same
engine files, strategy key, source-code pointers, exact vrun command, artifact
inputs (path, SHA-256, window, bars) and the metrics the other engine must
reproduce. This is a reproduction index, not a new verdict.
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, 'code')
RUNS = os.path.join(ROOT, 'results', 'runs')
RANK = os.path.join(ROOT, 'results', '_top100_2026_11_09_rank.json')
OUT_JSON = os.path.join(ROOT, 'results', 'top100_2026-11-09_strategies.json')
OUT_MD = os.path.join(ROOT, 'results', 'top100_2026-11-09_repro.md')


def find_lines(path, pattern):
    if not os.path.exists(path):
        return []
    rx = re.compile(pattern)
    hits = []
    with open(path, encoding='utf-8', errors='ignore') as fh:
        for i, line in enumerate(fh, 1):
            if rx.search(line):
                hits.append(i)
    return hits


def first_line(path, pattern):
    hits = find_lines(path, pattern)
    return hits[0] if hits else None


def qs_ref(code):
    files = ['qs_strats.py', 'qs_c_strats.py', 'qs_d_strats.py',
             'qs_flow_strats.py', 'qs_b_strats.py']
    for fn in files:
        p = os.path.join(CODE, fn)
        line = first_line(p, re.escape(f'"{code}"'))
        if line:
            return {'file': fn, 'token': code, 'line': line}
    return None


def pack50_ref(pid):
    p = os.path.join(CODE, 'pack50_strats.py')
    fn = f'b{pid:02d}'
    line = first_line(p, rf'^def {re.escape(fn)}\b')
    reg = first_line(p, rf'^\s+{pid}: dict')
    return {'file': 'pack50_strats.py', 'token': fn, 'line': line, 'registry_line': reg}


def cbpack_ref(sid, engine_file):
    fn = {'S01': 's01_tfd', 'S02': 's02_dfb', 'S03': 's03_sqz',
          'S04': 's04_vwf', 'S05': 's05_tpb', 'S06': 's06_sbo',
          'S07': 's07_fun', 'S08': 's08_oip', 'S09': 's09_lsr',
          'S10': 's10_tsm'}.get(sid)
    if not fn:
        return None
    p = os.path.join(CODE, engine_file)
    line = first_line(p, rf'^def {re.escape(fn)}\b')
    spec = first_line(p, re.escape(f'StrategySpec("{sid}"'))
    return {'file': engine_file, 'token': fn, 'line': line, 'spec_line': spec}


def pack20_ref(name):
    p = os.path.join(CODE, 'pack20_engine.py')
    if not name:
        return None
    line = first_line(p, re.escape(f'"{name}":'))
    fn = None
    with open(p, encoding='utf-8', errors='ignore') as fh:
        for raw in fh:
            if re.search(rf'"{re.escape(name)}"\s*:\s*([A-Za-z_]\w*)', raw):
                fn = re.search(rf'"{re.escape(name)}"\s*:\s*([A-Za-z_]\w*)', raw).group(1)
                break
    def_line = first_line(p, rf'^def {re.escape(fn)}\b') if fn else None
    return {'file': 'pack20_engine.py', 'token': name, 'line': line, 'function': fn, 'function_line': def_line}


def generic_ref(adapter, engine_files):
    token = {
        'botstrat': 'run', 'cvrmd': 'run', 'rsimr': 'execute',
        'smqe11': 'run_symbol', 'qs096': 'build_plan', 'qs097': 'build_plan',
    }.get(adapter)
    refs = []
    for fn in engine_files or []:
        if not token:
            continue
        p = os.path.join(CODE, fn)
        line = first_line(p, rf'^def {re.escape(token)}\b')
        if line:
            refs.append({'file': fn, 'token': token, 'line': line})
    return refs


def strategy_key_and_refs(row, art):
    adapter = art.get('strategy') or row.get('adapter')
    params = art.get('params') or {}
    metrics = art.get('metrics') or {}
    engine_files = (art.get('provenance') or {}).get('engine_files') or []
    refs = []
    key = None
    if adapter in ('qs', 'qsd') and isinstance(params.get('strat'), str):
        key = params['strat']
        r = qs_ref(key)
        if r:
            refs.append(r)
    elif adapter in ('qsf', 'qsb', 'qsc'):
        key = params.get('strat') or params.get('card')
        if isinstance(key, str):
            r = qs_ref(key)
            if r:
                refs.append(r)
    elif adapter == 'top10' and isinstance(params.get('id'), int):
        key = str(params['id'])
        fn = f's{key}'
        line = first_line(os.path.join(CODE, 'top10_engine.py'), rf'^def {re.escape(fn)}\b')
        refs.append({'file': 'top10_engine.py', 'token': fn, 'line': line,
                     'registry_line': first_line(os.path.join(CODE, 'top10_engine.py'),
                                                  re.escape(f'"{key}":'))})
    elif adapter == 'pack50' and isinstance(params.get('strat'), int):
        key = f'S{params["strat"]}'
        refs.append(pack50_ref(params['strat']))
    elif adapter == 'pack20':
        name = metrics.get('strategy_name') or row.get('label')
        name = re.sub(r'^\d+\s+', '', str(name or '')).strip()
        key = name or str(params.get('id'))
        r = pack20_ref(name)
        if r:
            refs.append(r)
    elif adapter in ('cbpackf', 'eqpack'):
        table_id = None
        label = str(row.get('label') or '')
        for t in art.get('tables') or []:
            if isinstance(t, dict) and (t.get('name') or '') and (t.get('name') in label or label in (t.get('name') or '')):
                table_id = t.get('id')
                break
        if table_id:
            key = table_id
            engine_file = 'cbpack_funding_engine.py' if adapter == 'cbpackf' else 'cbpack_engine.py'
            r = cbpack_ref(table_id, engine_file)
            if r:
                refs.append(r)
    elif adapter == 'dspack':
        key = params.get('strat')
        if key == 'ds1':
            line = first_line(os.path.join(CODE, 'deepseek_pack.py'), r'^def strat_tsmom\b')
            refs.append({'file': 'deepseek_pack.py', 'token': 'strat_tsmom', 'line': line})
    elif adapter == 'dspack2':
        key = params.get('strat')
        if key == 'ds7':
            line = first_line(os.path.join(CODE, 'deepseek_pack2.py'), r'^def strat_rsi2\b')
            refs.append({'file': 'deepseek_pack2.py', 'token': 'strat_rsi2', 'line': line})
    elif adapter in ('botstrat', 'cvrmd', 'rsimr', 'smqe11', 'qs096', 'qs097'):
        key = adapter
        refs = generic_ref(adapter, engine_files)
    else:
        key = params.get('strat') or params.get('card') or params.get('id')
    return key, refs


def rel_input(inp):
    p = inp.get('path') or ''
    try:
        p = os.path.relpath(p, ROOT)
    except ValueError:
        pass
    keep = {k: inp.get(k) for k in
            ('bars', 'end', 'gap_breach', 'max_gap_bars', 'missing_bars', 'path',
             'sha256', 'start', 'cut_ts') if inp.get(k) is not None}
    keep['path'] = p
    return keep


def costs(art):
    out = {}
    metrics = art.get('metrics') or {}
    prov = art.get('provenance') or {}
    for k in ('fee_bps_per_side', 'slippage_bps_per_side', 'cost_bps_per_side',
              'fee_bps', 'slippage_bps', 'cost_rt_bps', 'cost_mode', 'funding_charged'):
        if isinstance(metrics.get(k), (int, float, str, bool)):
            out[k] = metrics[k]
    if isinstance(prov.get('costs'), dict):
        out['provenance.costs'] = prov['costs']
    if 'funding' in prov:
        out['provenance.funding'] = prov['funding']
    if 'funding_charged' in prov:
        out['funding_charged'] = prov['funding_charged']
    return out


def main():
    rows = json.load(open(RANK, encoding='utf-8'))[:100]
    entries = []
    for rank, row in enumerate(rows, 1):
        rid = row['run_id']
        art = json.load(open(os.path.join(RUNS, rid + '.json'), encoding='utf-8'))
        key, refs = strategy_key_and_refs(row, art)
        entries.append({
            'rank': rank,
            'label': row.get('label'),
            'adapter': art.get('strategy') or row.get('adapter'),
            'symbol': art.get('symbol') or row.get('symbol'),
            'timeframe': art.get('timeframe') or row.get('tf'),
            'run_id': rid,
            'strategy_key': key,
            'engine_files': (art.get('provenance') or {}).get('engine_files'),
            'engine_sha256': (art.get('provenance') or {}).get('engine_sha256'),
            'engine_version': (art.get('provenance') or {}).get('engine_version'),
            'params': art.get('params') or {},
            'same_engine_command': art.get('cmd'),
            'same_engine_command_template': (
                f"python code/vrun.py run --strategy {art.get('strategy')} --tf {art.get('timeframe')} "
                f"--symbol {art.get('symbol')}"
                + (f" --params '{json.dumps(art.get('params') or {}, separators=(',', ':'))}'"
                   if (art.get('params') or {}) else '')),
            'inputs': [rel_input(x) for x in (art.get('inputs') or [])],
            'costs': costs(art),
            'source_refs': refs,
            'target_metrics': {
                'return_pct': row.get('ret'),
                'profit_factor': row.get('pf'),
                'n_trades': row.get('n'),
            },
        })
    json.dump(entries, open(OUT_JSON, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    lines = [
        '# Cómo replicar las cien estrategias en otro motor',
        '',
        'El índice máquina está en `results/top100_2026-11-09_strategies.json`.',
        'Cada entrada trae: ranking, estrategia, adapter, símbolo/timeframe,',
        '`run_id`, clave de estrategia, ficheros de motor, referencias de código,',
        'comando exacto del motor original, parámetros, inputs con SHA-256 y',
        'métricas objetivo (`return_pct`, `profit_factor`, `n_trades`).',
        '',
        'Para comprobarla en otro motor, en orden:',
        '',
        '1. Copia el slice de datos exacto: usa `inputs`; respeta `start`, `end`,',
        '   `bars`, `sha256` y `cut_ts`. Si hay funding en inputs, inclúyelo.',
        '2. Conecta la señal desde `source_refs`: el token y línea apuntan a la',
        '   función o registro de la estrategia en el motor de este repo.',
        '3. Replica la ejecución declarada: señal en cierre, fill en la apertura',
        '   siguiente, stop/target intrabar con stop primero cuando el engine lo',
        '   declare, y los costes/funding de `costs`.',
        '4. Compara, en el mismo orden de columnas, el retorno neto, el profit',
        '   factor y el número de trades contra `target_metrics`.',
        '',
        'La vía byte-exacta es el `same_engine_command` de cada entrada.',
        'Si el executor de tu motor difiere en el timing, costes o funding, no copies',
        'solo la señal: primero iguala la ejecución y después el sizing.',
    ]
    open(OUT_MD, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    print(f'wrote {len(entries)} entries to {OUT_JSON}')
    print(f'wrote {OUT_MD}')


if __name__ == '__main__':
    sys.exit(main())
