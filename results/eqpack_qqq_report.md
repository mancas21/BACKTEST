# eqpack — cbpack's ten rule strategies on QQQ daily (first equities campaign)

Date of record: 2026-10-29. Data: `data/alpaca_1d/QQQ_1d.csv` — 2722 daily bars,
2016-01-04 to 2026-10-29, Alpaca SIP tape, split-and-dividend adjusted, manifest
`data/ALPACA_EQUITIES_IMPORT.json` (sha256 844adcc1e80e...). Engine:
`code/cbpack_engine.py` used UNMODIFIED (hash-locked, sha 055b584de9aa... —
the historically audited executor). Pre-run audit:
`results/eqpack_audit_known_answers.txt` — eight checks ALL PASS (engine-lock,
the htf-adaptation semantics, the load path, the declared candle-proxy flow,
the self-skips, a no-lookahead truncation proof through the adapter path, the
pack's end_of_data close convention, determinism).

Declared adaptations, uniform across every strategy (no per-strategy picks):
`htf=1440` for the three strategies that carry an `htf` parameter (S01, S02,
S05) — on daily bars this reproduces exactly the pack's one-hour semantics,
where the HTF filter equalled the chart timeframe; flow uses the pack's own
declared candle-proxy fallback (equities have no taker split); S06 is excluded
(intraday UTC sessions do not exist on daily bars) and S07/S08 self-skip (no
funding / open interest on equities). Sizing is the pack's own default
(stop-risk of one percent per trade, three-times leverage cap), which on daily
ATR stops keeps notional well under one times equity — the exposure column
below is measured per artifact. Costs: `eq` = 0.1 bps fee + 0.5 bps slippage
per side (Alpaca zero commission, SEC/TAF amortised, liquid-ETF spread),
round trip 1.2 bps; `cons` = one plus one bps per
side, round trip 4 bps; the zero-cost control
runs inside every artifact and the drag is measured there.

## VERDICT: KILLED as alpha — zero of seven strategies pass the gate and none beats buy & hold

Counted from the two artifacts below: zero of
seven runnable strategies pass the full gate at equities costs,
zero of seven beat buy & hold on the same bars
(QQQ itself did 607.07% over the decade). The failures are
sample, concentration and the passive benchmark — NOT costs: the measured drag
stays under 1.46
percentage points even at the conservative regime, so unlike the crypto
campaigns below one hour, equities costs do not destroy this pack. What kills
it is everything else:

- The two closest cells, S01 (PF 1.427, 81 trades,
  top-five share 53%) and S05 (PF 1.411,
  99 trades, top-five 64%), fail the
  green-years gate by one year: seven of eleven
  green where the gate asks for at least two thirds.
- S02 shows the best profit factor (2.192) with its best five trades
  carrying 99% of total PnL — one trade away from
  the concentration kill, on 39 trades.
- S10's profit factor of 6.353 rests on 10 closed trades
  with a top-five share of 116% — no sample.
- S03 (four trades) and S09 (thirteen trades, top-five
  849% of PnL) are noise. S04 loses
  outright (PF 0.826).

The honest reading: at equities costs this pack carries a small, real gross
edge on some rules (S01, S02, S05 are positive and PF-above-one in both cost
regimes), but the drawdown profile (three to fourteen percent max DD against
QQQ's own much deeper crashes) means the pack behaves as a risk-reducer, and
as alpha it is nowhere near the passive benchmark. Per the standing rule — no
rescue loops, no parameter tuning, no window picking.

## Results — QQQ daily, costs `eq` (0.1 + 0.5 bps per side)

Artifact 68c93ae390084b18.

| id | name | n | net % | PF | win % | maxDD % | top-5 % | cost/gross % | h1 % | h2 % | green | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S01 | Taker-Flow Drift Bands | 81 | 24.18 | 1.427 | 43.2 | -6.1 | 53 | 0.3 | 17.9 | 5.3 | seven of eleven | fail |
| S02 | Donchian + Flow Breakout | 39 | 25.24 | 2.192 | 46.2 | -9.8 | 99 | 0.1 | 8.4 | 15.5 | seven of eleven | fail |
| S03 | Squeeze Release | 4 | 1.48 | 1.582 | 50.0 | -2.7 | 272 | 0.2 | 0.0 | 1.5 | two of eleven | fail |
| S04 | VWAP Fade (range regime only) | 57 | -6.51 | 0.826 | 29.8 | -14.1 | — | — | -10.4 | 4.4 | seven of eleven | fail |
| S05 | HTF Trend Pullback (RSI-2) | 99 | 11.43 | 1.411 | 67.7 | -3.7 | 64 | 0.6 | 4.5 | 6.6 | seven of eleven | fail |
| S09 | Liquidity Sweep Reversal | 13 | 1.20 | 1.133 | 38.5 | -5.2 | 849 | 1.1 | 6.8 | -5.2 | three of eleven | fail |
| S10 | Vol-Targeted Time-Series Momentum | 10 | 21.54 | 6.353 | 60.0 | -6.7 | 116 | 0.0 | 4.4 | 16.4 | seven of eleven | fail |
| S06 | Session Range Breakout (UTC) | — | — | — | — | — | — | — | — | — | — | intraday UTC session strategy; daily bars carry no session s |
| S07 | Funding Extreme Fade | — | — | — | — | — | — | — | — | — | — | SKIPPED: missing ['funding_rate'] |
| S08 | OI / Price Regime | — | — | — | — | — | — | — | — | — | — | SKIPPED: missing ['open_interest'] |

## Results — QQQ daily, costs `cons` (1 + 1 bps per side)

Artifact fbe10ed77bdcc9b8.

| id | name | n | net % | PF | win % | maxDD % | top-5 % | cost/gross % | h1 % | h2 % | green | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S01 | Taker-Flow Drift Bands | 81 | 23.42 | 1.411 | 43.2 | -6.2 | 54 | 3.4 | 17.6 | 5.0 | seven of eleven | fail |
| S02 | Donchian + Flow Breakout | 39 | 24.81 | 2.163 | 46.2 | -9.8 | 100 | 1.2 | 8.2 | 15.3 | seven of eleven | fail |
| S03 | Squeeze Release | 4 | 1.44 | 1.560 | 50.0 | -2.7 | 279 | 2.4 | 0.0 | 1.4 | two of eleven | fail |
| S04 | VWAP Fade (range regime only) | 57 | -6.94 | 0.816 | 29.8 | -14.3 | — | — | -10.7 | 4.2 | six of eleven | fail |
| S05 | HTF Trend Pullback (RSI-2) | 99 | 10.39 | 1.372 | 67.7 | -3.8 | 69 | 6.6 | 4.0 | 6.1 | six of eleven | fail |
| S09 | Liquidity Sweep Reversal | 13 | 1.04 | 1.114 | 38.5 | -5.2 | 978 | 11.7 | 6.6 | -5.2 | three of eleven | fail |
| S10 | Vol-Targeted Time-Series Momentum | 10 | 21.48 | 6.309 | 60.0 | -6.7 | 116 | 0.2 | 4.4 | 16.4 | seven of eleven | fail |
| S06 | Session Range Breakout (UTC) | — | — | — | — | — | — | — | — | — | — | intraday UTC session strategy; daily bars carry no session s |
| S07 | Funding Extreme Fade | — | — | — | — | — | — | — | — | — | — | SKIPPED: missing ['funding_rate'] |
| S08 | OI / Price Regime | — | — | — | — | — | — | — | — | — | — | SKIPPED: missing ['open_interest'] |

## How to reproduce

    python code/_eqpack_audit.py
    python code/vrun.py run --strategy eqpack --tf 1d --symbol QQQ
    python code/vrun.py run --strategy eqpack --tf 1d --symbol QQQ --set costs=cons
    python code/vrun.py pverify --ids 68c93ae390084b18,fbe10ed77bdcc9b8 --quiet
    python code/vrun.py guard --report results/eqpack_qqq_report.md

The adapter accepts any symbol with a `data/alpaca_1d/<SYM>_1d.csv` file
(SPY, AAPL, MSFT, NVDA are already on disk).
