import json
import os

rids_two = [
    ('BTCUSDT', '1h', 'f61f67da44e8e6f4'), ('ETHUSDT', '1h', 'fd43dd67a3068bc0'),
    ('SOLUSDT', '1h', '2b7bc76f88084065'), ('HYPEUSDT', '1h', 'b40a5849ce250b0e'),
    ('SUIUSDT', '1h', 'c5b378e2fe5164de'), ('JUPUSDT', '1h', '8cbd8fbceb012a8b'),
    ('BTCUSDT', '15m', '42ad81c44e9c9d0c'), ('ETHUSDT', '15m', '198362ff2c2e25d3'),
    ('SOLUSDT', '15m', 'b55f4301053944a2'), ('HYPEUSDT', '15m', 'a88f971ee1527420'),
    ('SUIUSDT', '15m', '3ec0d54f11504814'), ('JUPUSDT', '15m', '16969105cfd00966'),
    ('BTCUSDT', '5m', '9fa6c0a8a3eb5bb0'), ('ETHUSDT', '5m', '3a943270bf65e5ec'),
    ('SOLUSDT', '5m', '7551f99611d9d726'), ('HYPEUSDT', '5m', '3bec7a6761b21ff9'),
    ('SUIUSDT', '5m', '0b572cdf8ab1ed10'), ('JUPUSDT', '5m', '23da5d4b40a3ddc9'),
]
rids_long = [
    ('BTCUSDT', '1h', '047ef2f8614a37ca'), ('ETHUSDT', '1h', 'edc5ba169c45a95d'),
    ('SOLUSDT', '1h', '8ed036d36fd794be'), ('HYPEUSDT', '1h', 'be52b88c5d390e51'),
    ('SUIUSDT', '1h', 'ca6a8091520a5ca5'), ('JUPUSDT', '1h', 'f35297aca084093e'),
]

lines = [
    '# QS-096 Report — Market-structure reversal plus volatility filter',
    '',
    '## Two-Sided Matrix (Repo Cost 11 bps RT)',
    '',
    '| symbol | tf | run_id | n | net % | PF | win % |',
    '|---|---|---|---:|---:|---:|---:|',
]
for sym, tf, rid in rids_two:
    art = json.load(open(f'results/runs/{rid}.json'))
    m = art['metrics']
    lines.append(f'| {sym} | {tf} | `{rid}` | {m["n_trades"]} | {m["return_pct"]:.2f} | {m["profit_factor"]:.3f} | {m["win_rate"]:.1f} |')

lines.append('')
lines.append('## Long-Only (1h)')
lines.append('')
lines.append('| symbol | run_id | n | net % | PF | win % |')
lines.append('|---|---|---:|---:|---:|---:|')
for sym, tf, rid in rids_long:
    art = json.load(open(f'results/runs/{rid}.json'))
    m = art['metrics']
    lines.append(f'| {sym} | `{rid}` | {m["n_trades"]} | {m["return_pct"]:.2f} | {m["profit_factor"]:.3f} | {m["win_rate"]:.1f} |')

lines.append('')
with open('results/qs096_report.md', 'w') as f:
    f.write('\n'.join(lines) + '\n')
print('Report written successfully')
