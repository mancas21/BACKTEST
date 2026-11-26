# Pre-registration — EMA×VWAP Suite 2 (#101–150)

Date: 2026-11-26. Written BEFORE the first artifact of this campaign exists.
The user chose the same grid as Suite 1: **one pair per row**, BTCUSDT.

## Scope and data

* One artifact per numbered row on BTCUSDT at the row's declared timeframe.
* The attachment asks for 3m bars; there is no native 3m CSV, so the adapter
  serves the BTC 1m file and the engine resamples it to 3m by grouping three
  consecutive 1m bars (OHLC first/max/min/last, volume summed). This is a
  declared DERIVED bar, not an independent download; it is new to Suite 2
  because Suite 1 skipped the 3m rows instead of resampling.
* 5m, 15m and 1h rows use the real native CSVs. The 1m source and the native
  files are hash-bound into the run_id exactly as served.
* Rows 148 and 149 are the only cross-sectional exceptions: they rank
  signals across the symbols that actually have the needed bars (15m panel
  for #148, 1h panel for #149). Their inputs are all those CSVs; the
  pseudo-symbol is `X15` / `X1H`. The universe is the BTC-native set that
  exists on disk, not a guessed seventeen.
* Funding is charged at real settlements from the BTC funding JSON on every
  perp row; the resampled 3m rows use the same 1m-sliced funding schedule.

## Skeleton and control

The shared skeleton is the Suite 1 base: EMA 11 × daily VWAP, cross arms a
five-bar setup, first close beyond both enters at the next open, close back
across EMA 11 exits at the next open, shorts mirror, one position, no
re-fitting. Each row changes only what its table says. The control is the
unmodified base computed INSIDE every artifact on the same served slice
(the attachment calls it Suite 1 #2; that exact cell could not be run in
Suite 1 because no 3m CSV existed, so this is its declared resampled
equivalent). A row only counts if it beats that control net of costs
out of sample.

## Costs, gates, trials

* Repo gate 11 bps RT, with 14 and 22 bps sensitivities and a zero-cost
  control measured inside each artifact. Row 104 uses the declared 2 bps
  limit-fill model with missed orders counted separately.
* Same screen as Suite 1 plus the control comparison: net > 0, PF > 1.2,
  n ≥ 30, positive test half, bootstrap LB > 0, top-5 concentration < 100%,
  and control-relative net positive out of sample. DD P95 and buy & hold are
  published but not used as a gate here (Suite 1 didn't gate on them).
* These are 50 more trials on top of Suite 1's 50: DSR uses **N = 100**,
  declared before running. Selection among survivors would be post-hoc and
  is not part of this campaign.
* The inversion block (D) is read gross-first: a gross gain that costs erase
  is reported as such, never as a rescue of the base signal.

## Addendum, 2026-11-26 (antes de la corrida de mercado)

Las filas **148 y 149** requieren un libro cross-sectional de selección por
fuerza de señal (top-2 largo/top-2 corto; y par largo-corto), que no está
implementado con fidelidad en este engine de un solo par. Se declaran
**NO DATA** y no se les asigna ningún número, en lugar de publicar una cifra
de un libro que no se ejecutó. Las otras cuarenta y ocho filas sí se corren
con el esqueleto de un par.

## Falsifiable expectations

* Cost-aware gates (C) and selectors (#148–149) are the rows most likely to
  cut trade count; if they still lose net, the base has no operable edge.
* The control-relative comparison is measured in-artifact, not assembled by
  the reader; each artifact asserts `eq[-1] − INIT == sum(pnl)`.
* `code/_emavwapv2_audit.py` must pass before any market number; `pverify`
  clean on all artifacts; `guard --strict` exit 0 on the report. Counts in
  words, every number beside its `run_id`.
