# Pre-registration — MTF top-down strategy (source `mtf_topdown.py`)

Date: 2026-11-26. Written BEFORE the first artifact of this campaign exists.
The user chose **SOLUSDT only**, on the 5m base with the repo's data.

## What the source is

`Downloads/mtf_topdown-strategy-claude.py` is a complete Python strategy:
signal stack (4H direction → 1H structure → 15M sweep → 5M MSS), its own
causal multi-timeframe resampling, its own backtest engine, causality tests
and a CLI. It is **not** a natural-language spec. Per AGENTS.md, the SIGNAL
is ported by importing the source's functions by identity (byte-identical
copy in `code/`, hash bound into every run_id) and the EXECUTION conventions
are declared by the harness on top.

## Declared execution conventions

* The source's `build_features()` and `swings()` are used unchanged; higher
  timeframes are resampled from the served 5m slice and aligned on bar CLOSE
  time, so no future HTF bar is visible. Swings confirm `n` bars late.
* Entry at the NEXT 5m open; SL-first when both SL and TP are touched in the
  same bar; gap-through fills at the open; ATR buffer from the 15m ATR;
  one position; 1% risk sizing with 10x leverage cap; time stop and EOD
  exit as in the source.
* The source's own cost block is 4 bps taker + 1 bps slippage per side and
  NO funding. The harness headline uses the repo gate (5.0 fee + 0.5 slip
  bps per side = 11 bps RT) **plus funding charged at the real BTC/SOL
  settlement instants on open notional**. Author cost and zero-cost/no-
  funding controls are measured inside the same artifact on identical signals.
* Funding attribution is inside each trade's PnL so
  `eq[-1] − INIT == sum(pnl)` closes inside the artifact.

## Cells

One SOLUSDT 5m cell for the repo regime. No parameter grid and no tuning:
the source's `Cfg()` defaults are frozen, with `allow_long`/`allow_short`
both true. Any variant (long-only, short-only, author costs, zero costs) is
an in-artifact control on the same signals, not a separate promoted cell.

## Validation before publication

* Byte-identical source copy verified by sha256 against the attachment.
* `code/_mtf_topdown_audit.py`: (1) the source's own `test_causality()`
  passes on real SOL 5m; (2) parity — the harness executor with the source's
  fee/slip and funding off reproduces the source's `backtest()` trades
  exactly on the same slice; (3) known answers for both directions, SL-first
  ties and gap fills; (4) accounting invariant asserted in every artifact.
* `pverify` bit-for-bit clean; `guard --strict` exit 0 on the report. Every
  number beside its `run_id`; counts in words.
* Verdict: the repo's screen (PF > 1.2, n ≥ 100, positive test half,
  bootstrap > 0, no extreme concentration, beats buy & hold), plus a
  funding/cost decomposition showing which regime contains the result.
  A zero-cost gain is a control, never a pass.
