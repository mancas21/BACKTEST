import json
p = '/home/ubuntu/of-collector/data/orderflow_raw/SUIUSDT/2026-09-19.depth_checkpoints.jsonl'
n = 0
keys = None
has_E = 0
has_recv = 0
with open(p, encoding='utf-8') as f:
    for line in f:
        try:
            o = json.loads(line)
        except Exception:
            continue
        n += 1
        if keys is None:
            keys = sorted(o.keys())
        if 'E' in o:
            has_E += 1
        if 'collector_recv_ms' in o:
            has_recv += 1
print('lines=', n, 'keys=', keys, 'has_E=', has_E, 'has_recv=', has_recv)
