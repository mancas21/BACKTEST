#!/usr/bin/env python3
"""_find_duplicate_data.py — exact duplicate detection over data/ + recorder/data.

Hashes every file (SHA-256, streamed) and groups identical content. A group with
more than one path is duplication that `du`-style accounting hides, because the
same bytes can live under two names (`binance_klines_1m` vs `_taker`, a panel
copy, a rotated parquet segment, etc.).

Read-only: prints groups, never deletes. Output is sorted by wasted bytes.
"""
from __future__ import annotations

import hashlib
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROOTS = [ROOT / "data", ROOT / "recorder" / "data"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    by_hash: dict[str, list[Path]] = defaultdict(list)
    total = 0
    files = 0
    for base in ROOTS:
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            try:
                size = p.stat().st_size
            except OSError:
                continue
            if size == 0:
                continue
            total += size
            files += 1
            by_hash[sha256_file(p)].append(p)

    groups = [(h, ps) for h, ps in by_hash.items() if len(ps) > 1]
    wasted = 0
    rows = []
    for h, ps in groups:
        size = ps[0].stat().st_size
        wasted += size * (len(ps) - 1)
        rows.append((size * (len(ps) - 1), size, len(ps), ps))
    rows.sort(reverse=True)

    print(f"ficheros hasheados: {files}   total: {total / 1024 / 1024:.1f} MiB")
    print(f"grupos duplicados: {len(groups)}   desperdicio exacto: {wasted / 1024 / 1024:.1f} MiB")
    print()
    for w, size, n, ps in rows[:40]:
        rel = [str(p.relative_to(ROOT)) for p in ps]
        print(f"{w / 1024 / 1024:9.2f} MiB desperdiciados  ({n} copias de {size / 1024 / 1024:.2f} MiB)")
        for q in rel:
            print(f"    {q}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
