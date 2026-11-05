# Sonnet 100-prompt pack — audit and backtest report

Date of record: 2026-10-29. Source: `Downloads/strategy_prompts_100-sonnet-claude.md` (100 prompts, numbered 01..100). Engine: `code/pack100_engine.py` on the frozen pack50_core execution machinery (next-open fills, SL-first ties, funding at the settlement instants), adapter `pack100`. Every number below is read from a persisted artifact cited by its run_id. Multi-TF prompts expand one cell per timeframe per the pack's own template; the headline cost is the repo gate (5.0 fee + 0.5 slip bps per side) because the pack declares no cost block; 2x, breakeven and zero-cost controls are measured inside every artifact. NO DATA, never estimated: the fourteen NVDA prompts, open-interest 95, long/short-ratio 96 and JUP funding 94.

## VERDICT: KILLED — zero of one hundred prompts produce a risk-specified pass

Two hundred and thirty-three cells were measured (two further cells, C37 at 15m and 1h, produced zero trades because the prompt's own box filter never qualified — that is the measurement). The gate outcome:

- Before a single basis point of cost, the median prompt is a coin flip: the median zero-cost profit factor rounds to one. Only twenty-three of two hundred and thirty-two cells clear a zero-cost profit factor of one point two; the rest have no gross edge to protect.

- The median cell's breakeven side cost is a fraction of a basis point — against the five and a half the repo gate charges. thirteen of two hundred and twenty-nine cells have a breakeven at or above the eleven-basis-point roundtrip; for the rest, costs are an order of magnitude larger than the edge.

- twenty-three of two hundred and thirty-three cells end with a positive net return at repo costs; the median cell loses most of the account, and many 5m/15m books are Ruined (minus one hundred percent).

- Three cells pass the joint v1 (G1-G6) and v2 statistical gate sets — all three are the SAME prompt (68, order-block retest on ETH, at 5m/15m/1h), and all three are declared a SIZING ARTIFACT below. With prompt 68 excluded: zero passers in one hundred.

## Prompt 68: the only passer, and why its numbers are not a claim

- `e700ec8b52943139` (F68-5m, ETHUSDT 5m): n 4033, net return +37001492.21 percent, PF 4.5793, zero-cost PF 8.6554, expectancy LB 26.613 bps, breakeven side cost 21.68 bps, maxDD 12.33 percent, p95 maxDD 11.93 percent.

- `ab11d9e0d116a63b` (F68-15m, ETHUSDT 15m): n 1412, net return +72231281.59 percent, PF 11.2887, zero-cost PF 15.9407, expectancy LB 79.63 bps, breakeven side cost 54.1 bps, maxDD 6.73 percent, p95 maxDD 9.4 percent.

- `e623e7768e7ad2e3` (F68-1h, ETHUSDT 1h): n 413, net return +117224.53 percent, PF 8.5815, zero-cost PF 10.0988, expectancy LB 119.485 bps, breakeven side cost 94.34 bps, maxDD 22.57 percent, p95 maxDD 19.91 percent.

The signal itself carries real gross structure (zero-cost PF above eight on all three timeframes — the strongest gross book of any pack this repo has measured). But the net numbers are NOT tradable claims, for a declared reason: the pack executor sizes FULL EQUITY per trade (the pack50 family's declared convention), while prompt 68's stops are the height of ONE order-block candle — about a tenth to a third of one percent on 5m ETH. Full equity against a tenth-percent stop is a hundred-to-one risk per trade; the prompt's own spec (one percent risk per trade) is not what the executor implements, and the executor's stop fills carry no gap-through stress. The compounding of thousands of tiny-R full-equity wins is the entire source of the astronomical returns. The honest statement: prompt 68's signal survives costs and the statistical layer and is a CANDIDATE for a properly risk-sized re-test (one percent risk to the block stop, gap-aware fills) — nothing more.

## The near-misses (best of the rest, repo costs)

- `f891014338637e94` C43-1h (Donchian(55) + volatility filter, SUIUSDT 1h): n 151, net +92.46 percent, PF 1.3199, zero-cost PF 1.3801, expectancy LB -55.892 bps — v1=False, v2=False.

- `7ddacf18e0b5ba5a` D51-1h (relative-strength-vs-BTC (long), SUIUSDT+BTCUSDT 1h): n 307, net +78.63 percent, PF 1.2712, zero-cost PF 1.3871, expectancy LB -24.783 bps — v1=False, v2=False.

- `3223187f21cf6708` F74-15m (market-structure HH/HL trend, HYPEUSDT 15m): n 38, net +57.39 percent, PF 3.2057, zero-cost PF 3.378, expectancy LB -278.528 bps — v1=False, v2=False.

- `0e0d2501a65f1a81` B17-1h (EMA 20/50 trend + EMA200 filter (long), HYPEUSDT 1h): n 77, net +53.73 percent, PF 1.3813, zero-cost PF 1.4441, expectancy LB -51.529 bps — v1=False, v2=False.

- `c6563b78a748ac77` F74-5m (market-structure HH/HL trend, HYPEUSDT 5m): n 72, net +50.05 percent, PF 3.011, zero-cost PF 3.2966, expectancy LB -152.378 bps — v1=False, v2=False.

- `4eed428adc7d4237` C44-1h (fractal breakout, ETHUSDT 1h): n 381, net +29.25 percent, PF 1.1256, zero-cost PF 1.2103, expectancy LB -27.255 bps — v1=False, v2=False.

- `c02614d4b123dc0c` B27-1h (Aroon(25) trend (long), SUIUSDT 1h): n 348, net +14.51 percent, PF 1.1038, zero-cost PF 1.191, expectancy LB -30.881 bps — v1=False, v2=False.

- `0b4ac2680e4c5f0e` A01-15m (RSI14 L/S mean-reversion, SPXUSDT 15m): n 237, net +13.83 percent, PF 1.0833, zero-cost PF 1.213, expectancy LB -18.413 bps — v1=False, v2=False.

The near-misses fail on expectancy (negative bootstrap lower bounds), breakeven cost (below the gate), or both. The familiar pack pattern repeats: nothing here has a gross edge large enough for the cost wall, and the few gross-edge books (F74's HYPE structure, F68) die on sizing or sample.

## Provenance

- Adapter `pack100` registered in `code/vrun.py`; sources hashed: pack100_engine/strats(1-3), pack50_core, pack50b engine+strats, pack50d engine+strats, gate2.

- The port's smoke test caught ten distinct builder-bug classes BEFORE any artifact existed (argument-shape errors, a self-contradictory A03 entry, an inverted F68 short stop, a swapped supertrend return). Two further defects were caught by reading the results: the F68 short-stop inversion (its multi-billion-percent first run) and the A03 zero-signal contradiction. Every fix re-ran the full campaign; superseded generations verify REFUSED by design and are kept append-only.

- C37 at 15m and 1h: the prompt's box filter (forty-eight-bar range under three ATR) never qualified: zero trades, reported as measured.

