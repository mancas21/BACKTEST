# backtest-system — every strategy, measured, most of them dead

Artifact-backed backtesting of public trading strategies. Nothing here is
financial advice. Almost everything in this repo is a **killed** strategy —
that is the point: the lab shows its work.

Follow the lab on X: [@nftepml](https://x.com/nftepml) — "we ran the backtests
so you don't have to."

## What's here

- `code/` — the engines, harness (`vrun.py`) and audits. Every number in a
  report traces to an artifact in `results/runs/` (not shipped; see below).
- `content/specs.md` — **SPECS.md**: the exact recipe of every posted
  strategy, each citing the source file it was distilled from
  (`code/x_spec_check.py` verifies every numeric token against that source).
- `content/posts/` — the X threads, paste-ready, verdict-labeled.
- `results/` — reports (guard-checked where marked OK in `results/REPORTS.md`).
- `results/registry/strategies.jsonl` — the universe: one row per measured
  strategy, with verdicts and artifact ids.

## How to verify a number

1. Get the same public Binance data (klines + funding) — `code/fetch_*.py`
   scripts show the endpoints; data itself is not redistributed.
2. `python code/vrun.py run --strategy <adapter> --tf <tf> --symbol <pair>`
   reproduces the artifact; `python code/vrun.py verify <run_id>` proves it.
3. `python code/x_spec_check.py` verifies every numeric token in SPECS.md
   exists in its cited source file.

## Reading the verdicts

KILLED / REJECTED / FAIL / SUSPENDED / CANDIDATE — full legend in
`GATES_AND_RULES.md`. A CANDIDATE is a screen survivor, never a proven edge.
No strategy in this repo is sold as alpha; nothing is financial advice.

## License

No license is granted. All rights reserved — read the code, but reuse of the
engines or reports is not permitted without permission.
