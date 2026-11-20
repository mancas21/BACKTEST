# Pre-registration — the zero-cost / no-rules control on the top ten

Date: 2026-11-20. Written BEFORE the first artifact of the campaign exists.

## What this experiment is

The user asked for an experiment: take ten strategies from the already
identified hundred best books, **remove the costs and the rules**, re-run the
backtest over the same markets, and deliver a report.

This is therefore a **CONTROL, not a verdict**. It answers one question: *how
much of the top hundred's measured performance was cost, and what do the same
books do when nothing is charged?* It is never evidence of alpha, it never
resurrects a killed verdict, and no row of it may be cited as a gate pass. The
repo's kill list stands exactly as written (REGLA 1: a sibling's failure is not
a verdict on a new port, and equally a sibling's zero-cost number is not a
verdict on the book).

## Which ten

The ten are the **first ten rows of `results/top100_2026-10-31.md`**, in the
order that list already published. Nothing was selected on the outcome of this
experiment: the list predates it, and the rows are taken verbatim from the top.
Two of the ten rows are two different strategies inside the same artifact
(`cbpackf` XRPUSDT 1h), so the ten books come from nine adapter runs.

| row | book | market | adapter | ranking `run_id` |
|---:|---|---|---|---|
| 1 | XRP delta-neutral grid v1 | XRPUSDT 15m | `xrpneutral` | `295c21687960fadd` |
| 2 | F74-15m market-structure HH/HL trend | HYPEUSDT 15m | `pack100` (`strat=F74-15m`) | `3223187f21cf6708` |
| 3 | botstrat | SPXUSDT 1h | `botstrat` | `f2aa1050b118e54f` |
| 4 | S02 Donchian + Flow Breakout | QQQ 1d | `eqpack` (S02) | `68c93ae390084b18` |
| 5 | F74-1h market-structure HH/HL trend | HYPEUSDT 1h | `pack100` (`strat=F74-1h`) | `6ab39e80e1230277` |
| 6 | botstrat | BNBUSDT 1h | `botstrat` | `7059e662c6d737b5` |
| 7 | cvrmd | SUIUSDT 1h | `cvrmd` | `00c8c19179ea05ba` |
| 8 | S10 Vol-Targeted Time-Series Momentum | XRPUSDT 1h | `cbpackf` (S10) | `db89577d5f9d9d34` |
| 9 | S10 Vol-Targeted Time-Series Momentum | SOLUSDT 1h | `cbpackf` (S10) | `ded7cca009e13445` |
| 10 | S02 Donchian + Flow Breakout | XRPUSDT 1h | `cbpackf` (S02) | `db89577d5f9d9d34` |

## The two regimes

Every one of the nine runs is made TWICE, on the same frozen data cut, by the
same engine bytes, differing only in the cost block:

* **BASE** — the regime the book was published under: `cbpackf` 5.0 bps fee +
  0.5 bps slippage per side with funding charged at the real settlements;
  `xrpneutral` 2.0 bps maker / 5.0 bps taker fee + 2.0 bps slippage with
  funding charged; `pack100` 5.0 / 0.5 with funding charged; `botstrat` and
  `cvrmd` 6.0 / 0.5 (both kline-only, neither has ever charged funding);
  `eqpack` 0.1 / 0.5 (Alpaca equities, no funding exists).
* **ZERO** — fees 0.0, slippage 0.0 and funding NOT charged, in the same
  engine.

The comparison is inside the campaign: both numbers come from artifacts minted
today on today's bytes. The ranking artifacts are four weeks old and five of
the nine read data files that have grown since (`295c21687960fadd`,
`7059e662c6d737b5`, `00c8c19179ea05ba`, and the HYPE/XRP/SOL funding files), so
quoting the old number next to the new one would compare two different data
sets.

## What is NOT removed

"Las reglas" is read as **the repo's screening rules** — the gate battery
(PF floor, sample floor, period split, walk-forward, concentration, bootstrap,
buy & hold) — and the cost regime that sits inside it. Those are removed: this
campaign applies **no gate and publishes no pass/fail**.

The **execution conventions are untouched**, because they are the strategy, not
a rule laid on top of it: signal on the closed bar, fill at the next open,
stop-first on ties, gap-through at the open, the engine's own sizing and
leverage cap, one position at a time, real settlement instants where funding is
charged. Removing those would measure a different book.

## Falsifiable expectations, declared before running

* If a book was killed by cost, ZERO must move it above BASE, and the gap is the
  measured cost drag. Direction alone is not proof; the report shows both
  numbers, the trade count and the profit factor.
* If a book loses at ZERO as well, cost was never the binding constraint, and
  the report says so instead of blaming the fees.
* A ZERO number larger than BASE is **not** an edge claim: `xrpneutral`'s
  ranking row is the 15m OHLC book that the 1m fill audit later killed, and
  that caveat travels with the row.

## Mechanics

* Three adapters gain an explicit `costs` switch (`botstrat`, `cvrmd`,
  `pack100`); `cbpackf`, `xrpneutral` and `eqpack` already expose theirs.
* `botstrat`'s `load()` hardcodes `data/binance_klines_1h`; the adapter now
  points it at the directory of the served file, which makes the gen-2 cut
  hash describe the bytes the engine actually read (a provenance fix, no
  behaviour change when the served file is the real file).
* `code/_zerocost_audit.py` must pass before any market run: identity (BASE
  reproduces the engine's own output with its native constants), independent
  zero-cost recomputation (a freshly loaded engine with its constants set to
  zero reproduces the adapter's ZERO output exactly), and a regression check
  that BASE reproduces the published ranking number wherever the input bytes
  did not change.
* Every artifact asserts nothing about gates; `guard --strict` must pass on the
  report before it is published.

## Addendum, 2026-11-20 (after the audit, before publication)

The regime paragraph above describes `botstrat` and `cvrmd` as "6.0 / 0.5".
That was written from the adapters' declared shape and it is wrong about the
second constant: both engines carry `COST, SLIP = 0.0006, 0.0005`, which is
6 bps of commission **plus** 5 bps of slippage per side — the old 22 bps
round-trip preset, twice the repo's current 11 bps. The BASE artifacts record
both numbers (`fee_bps_per_side` 6.0, `slippage_bps_per_side` 5.0) and the
report prints them side by side; the ZERO regime (0.0 / 0.0) is unaffected, and
so is every conclusion. Nothing else in this pre-registration changes.
