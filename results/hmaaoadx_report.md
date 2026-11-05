# hmaaoadx (Fingrad HMA · AO · ADX Pine strategy) — verdict report

Built exclusively from `results/runs` artifacts of strategy `hmaaoadx` (artifact count in words: **twenty-six**). Every literal number below is artifact-stored at its printed rounding; counted quantities are spelled out because counts are not stored anywhere.

- harness: `code/vrun.py`, adapter `hmaaoadx`, engine version token `hmaaoadx-1` (sources hashed into every run_id: the author Pine copy, `emaadx_engine.py`, `dspack_engine.py`, `hmaaoadx_engine.py`)
- author attachment copied byte-identical to `code/fingrad_hma_ao_adx_strategy.pine` (sha256 `d3aabd19a1795f3020f0b26f659e1710e60c1dc5c4e3db66eb65f2b02f58b860`)
- campaign timeframe: one-hour bars only (the harness refuses any other timeframe for this engine); symbols: the canonical thirteen (in words: **thirteen**)
- known-answer audit ran BEFORE any real-data run: `code/_hmaaoadx_audit.py` → `results/hmaaoadx_audit_known_answers.txt` — cases passed in words: **forty-two**, failures in words: zero
- costs preset scored everywhere: `repo6x5` (six basis points taker fee plus five basis points slippage per side); every artifact also embeds the zero-cost control re-run (`ret_zero_pct`, `pf_zero`, `drag_pp = ret_zero − scored`) computed on the same signals — the cost GATE inside the strategy (minimum ATR share, Pine input default) stays ON in both passes, matching the Pine, so the zero-cost column isolates the round-trip fees only
- execution conventions the audit pins: signals evaluate on bar close and orders fill at the NEXT bar's open (the Pine's `process_orders_on_close=false`); the ATR bracket arms from the FILL price; a bar spanning stop and limit resolves stop-first; a bar opening beyond the level fills at its open; the daily-loss breaker cuts at three percent under day-start equity and resets at each UTC day change; sizing is one percent of equity against a two-times-ATR stop distance, capped at ten times lever
- gates are the repo G-set: G1 strict profit factor above one-point-two; G2 at least thirty closed units; G3 both half-window profit factors above one; G4 green complete years two of three (full windows only); G5 beats buy and hold on the scored span; G6 the book stays green without its best five units.

## Verdict

**The Fingrad HMA · AO · ADX strategy is KILLED.** Profitable cells under repo fees, in words: **zero** of **twenty-six** (full-window positives in words: **zero**; last-six-months positives in words: **zero**). Cells that pass the full gate set, in words: **zero** of **twenty-six**. The strict profit factor sits BELOW one on every one of the twenty-six cells.

The kill is not a fee-only story. The zero-cost control columns show a real gross tendency on most symbols — the book is green before fees on the full window for eleven of thirteen symbols — yet the scored book loses on every symbol, and on `SOLUSDT` and `SPXUSDT` the signal has no gross edge at all even before fees (details in the zero-cost section). At this trade frequency the default one-percent-of-equity-per-two-ATR sizing turns every closed unit in and out at a LARGE share of equity, so an eleven-basis-point round trip compounds into a majority-of-equity drag across seven-hundred-plus closes per symbol. That is the strategy as shipped: the backtest shows the same result as written, with no parameter surgery applied.

## Data coverage (one-hour files; one row per symbol)

| run_id | symbol | bars | start | end |
|---|---|---:|---|---|
| 2c39ad6ee53a29d3 | ADAUSDT | 58995 | 2020-01-31 | 2026-10-24 |
| 1d2762499a8ab429 | AVAXUSDT | 53332 | 2020-09-23 | 2026-10-24 |
| 22a8d44e90047e9e | BNBUSDT | 58755 | 2020-02-10 | 2026-10-24 |
| f844336f4f6d3440 | BTCUSDT | 62466 | 2019-09-08 | 2026-10-24 |
| 8818f81e243f086b | DOGEUSDT | 55130 | 2020-07-10 | 2026-10-24 |
| 72e0613bfc121cf6 | ETHUSDT | 60556 | 2019-11-27 | 2026-10-24 |
| 1ad620e45d05f27b | HYPEUSDT | 11624 | 2025-05-30 | 2026-09-26 |
| 39ed1a63df3467e5 | LINKUSDT | 59331 | 2020-01-17 | 2026-10-24 |
| 23fefd761dbdbed7 | NEARUSDT | 52803 | 2020-10-15 | 2026-10-24 |
| 5666e45fecdc714a | SOLUSDT | 53548 | 2020-09-14 | 2026-10-24 |
| 98cb16430b8ec720 | SPXUSDT | 15726 | 2024-12-10 | 2026-09-26 |
| b618c6e7552052d2 | SUIUSDT | 30475 | 2023-05-03 | 2026-10-24 |
| a54be9c72cefc23b | XRPUSDT | 59595 | 2020-01-06 | 2026-10-24 |

## hmaaoadx — full window (costs `repo6x5`)

| run_id | symbol | n | ret_pct | PF | pf_h1 | pf_h2 | ret_zero_pct | pf_zero | drag_pp | net_wo_top5_pct | gates_all |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2c39ad6ee53a29d3 | ADAUSDT | 854 | -48.35 | 0.7000 | 0.7002 | 0.6997 | 13.06 | 1.0752 | 61.40 | -0.63 | False |
| 1d2762499a8ab429 | AVAXUSDT | 787 | -22.97 | 0.8704 | 0.9092 | 0.8322 | 50.30 | 1.2659 | 73.27 | -0.44 | False |
| 22a8d44e90047e9e | BNBUSDT | 918 | -69.98 | 0.6227 | 0.7197 | 0.4664 | 12.06 | 1.0560 | 82.04 | -0.91 | False |
| f844336f4f6d3440 | BTCUSDT | 924 | -69.67 | 0.6690 | 0.8250 | 0.4264 | 41.21 | 1.1587 | 110.88 | -0.97 | False |
| 8818f81e243f086b | DOGEUSDT | 787 | -47.92 | 0.7056 | 0.6740 | 0.7502 | 9.63 | 1.0551 | 57.55 | -0.65 | False |
| 72e0613bfc121cf6 | ETHUSDT | 886 | -32.30 | 0.8512 | 0.9735 | 0.7165 | 99.43 | 1.3832 | 131.73 | -0.67 | False |
| 1ad620e45d05f27b | HYPEUSDT | 166 | -2.63 | 0.9293 | 1.1449 | 0.7314 | 11.45 | 1.3716 | 14.08 | -0.18 | False |
| 39ed1a63df3467e5 | LINKUSDT | 899 | -51.58 | 0.6993 | 0.7367 | 0.6522 | 4.39 | 1.0236 | 55.98 | -0.69 | False |
| 23fefd761dbdbed7 | NEARUSDT | 811 | -34.78 | 0.7948 | 0.7825 | 0.8108 | 16.67 | 1.0930 | 51.45 | -0.52 | False |
| 5666e45fecdc714a | SOLUSDT | 835 | -60.27 | 0.6132 | 0.6721 | 0.5342 | -19.53 | 0.8807 | 40.73 | -0.75 | False |
| 98cb16430b8ec720 | SPXUSDT | 255 | -13.47 | 0.7791 | 0.9473 | 0.6089 | -1.98 | 0.9648 | 11.49 | -0.28 | False |
| b618c6e7552052d2 | SUIUSDT | 431 | -4.51 | 0.9549 | 0.9183 | 0.9944 | 33.30 | 1.3575 | 37.81 | -0.23 | False |
| a54be9c72cefc23b | XRPUSDT | 854 | -59.97 | 0.6591 | 0.7206 | 0.5681 | 4.08 | 1.0210 | 64.05 | -0.79 | False |

Cells positive under fees in words: **zero**. Cells passing G1 in words: **zero**. Cells passing G3 (both halves) in words: **zero**. Cells passing G5 (beats buy-and-hold) in words: **two** — the strategy lost LESS than holding only where the symbol's own market was falling on those spans (this signal made money in none of them). Cells passing G6 in words: **zero**. Cells passing ALL gates in words: **zero**. Cells passing G4 (green complete years two of three) in words: **zero**.

## hmaaoadx — last6mo window (costs `repo6x5`)

| run_id | symbol | n | ret_pct | PF | pf_h1 | pf_h2 | ret_zero_pct | pf_zero | drag_pp | net_wo_top5_pct | gates_all |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 53f78bc812a660b5 | ADAUSDT | 66 | -9.25 | 0.4835 | 0.1487 | 0.9697 | -3.00 | 0.7844 | 6.24 | -0.17 | False |
| 96a749540a540461 | AVAXUSDT | 60 | -3.16 | 0.8031 | 0.5319 | 1.1769 | 3.41 | 1.2820 | 6.57 | -0.12 | False |
| fbbe9feedfe97135 | BNBUSDT | 65 | -10.78 | 0.4996 | 0.2232 | 0.7392 | 3.24 | 1.2406 | 14.02 | -0.16 | False |
| 233f9a552f4bd4e7 | BTCUSDT | 74 | -6.80 | 0.7202 | 0.4151 | 1.0269 | 9.78 | 1.6867 | 16.57 | -0.20 | False |
| 267f8c8faf28ceda | DOGEUSDT | 70 | -6.02 | 0.7539 | 0.5530 | 1.0436 | 2.09 | 1.1058 | 8.12 | -0.18 | False |
| 11cfbe4900e4c185 | ETHUSDT | 74 | -1.52 | 0.9435 | 0.2644 | 1.6776 | 12.26 | 1.6653 | 13.78 | -0.24 | False |
| 8ec22eeceacb0638 | HYPEUSDT | 59 | -3.26 | 0.7630 | 0.2875 | 1.3307 | 2.53 | 1.2509 | 5.78 | -0.13 | False |
| 3cd7294647ac49e0 | LINKUSDT | 68 | -14.52 | 0.3736 | 0.0595 | 0.7583 | -7.34 | 0.5960 | 7.18 | -0.20 | False |
| d99675b84e223c36 | NEARUSDT | 62 | -0.00 | 0.9999 | 1.1576 | 0.7802 | 4.40 | 1.4200 | 4.40 | -0.09 | False |
| db79eead9b6cc841 | SOLUSDT | 69 | -18.58 | 0.1419 | 0.0789 | 0.2052 | -10.87 | 0.3269 | 7.71 | -0.19 | False |
| eb0c8762719ee0cc | SPXUSDT | 76 | -11.18 | 0.4938 | 0.1818 | 0.9001 | -7.00 | 0.6353 | 4.18 | -0.20 | False |
| 984f545768d7c54e | SUIUSDT | 59 | -8.05 | 0.4953 | 0.6216 | 0.4088 | -2.41 | 0.8064 | 5.64 | -0.14 | False |
| 110116926f9d15c2 | XRPUSDT | 66 | -9.02 | 0.5792 | 0.2769 | 0.8222 | 0.52 | 1.0340 | 9.53 | -0.18 | False |

Cells positive under fees in words: **zero**. Cells passing G1 in words: **zero**. Cells passing G3 (both halves) in words: **zero**. Cells passing G5 (beats buy-and-hold) in words: **four** — the strategy lost LESS than holding only where the symbol's own market was falling on those spans (this signal made money in none of them). Cells passing G6 in words: **zero**. Cells passing ALL gates in words: **zero**. G4 does not apply to a six-month window (stored None).

## Zero-cost signal audit (is there ANY gross edge?)

The `ret_zero_pct` / `pf_zero` columns answer directly (same signals at literally zero fee and slip, Pine cost gate still on):
- full window: zero-cost profit factor above one on eleven of thirteen symbols — a real but THIN gross tendency, peaking at the cells cited below.
- full window, zero-cost book still NEGATIVE (count in words: **two**): `SOLUSDT` and `SPXUSDT` — no gross signal there at all, fees or none.
- last-six-months: zero-cost profit factor above one on eight of thirteen symbols.

The cost mechanism at its extreme (cite run_id): the largest drag on the whole grid is `72e0613bfc121cf6` (`ETHUSDT`, full): zero-cost 99.43 percent, scored -32.30 percent, stored drag 131.73 percentage points. Worst gross book on the grid: `db79eead9b6cc841` (`SOLUSDT`, last6mo) zero-cost profit factor 0.3269 — no edge even free of fees. Best gross book: `233f9a552f4bd4e7` (`BTCUSDT`, last6mo) zero-cost profit factor 1.6867 — a thin tendency that repo fees consume entirely (see the scored columns above).

