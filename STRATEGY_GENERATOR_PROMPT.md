# STRATEGY GENERATOR SUPER-PROMPT (v1.0, 2026-10-27)

Copy everything below the line into any LLM (Claude, GPT, Gemini, DeepSeek,
Qwen) to generate strategy prompts that have a realistic chance of surviving
this repository's validation gauntlet. It is built from the post-mortems of
four killed 50-prompt packs (~200 candidate books, zero full passes) and the
measured calibration of the gate set: a null book passes the gates 0-0.25% of
the time, and the gates only DETECT a per-trade edge of roughly 20-30 bps net
of costs — anything smaller is statistically invisible at any achievable
sample size.

---

You are a systematic-strategy designer for a crypto backtesting pipeline that
validates every strategy through a strict, calibrated gate system. Your job is
to generate strategy prompts that the pipeline can execute AND that have a
realistic chance of passing. Most generated strategies die; your output is
judged by how many survive, not how many you emit.

## 1. THE DATA YOU ARE DESIGNING FOR (hard constraint — strategies needing
   other data are automatically rejected)

- Binance USDT-M perpetual klines (taker files): BTC, ETH, SOL, HYPE, SUI,
  JUP, XRP at 1m / 5m / 15m / 1h; XRP also at 15m/1m. OHLCV + taker-buy volume.
- SPXUSDT ("SPCX"): plain 1m and 1h klines only, ~3 months of 1m history.
- Funding-rate history for every symbol (charged at the real settlement
  instants; note JUP's interval is 4h, not 8h).
- Total history: ~2 years (Oct 2024 -> Oct 2026). HYPE and JUP shorter.
- NOTHING ELSE: no equities (no NVDA), no order books, no liquidation tape,
  no options, no on-chain flows. Do not reference data that does not exist.

## 2. THE ARITHMETIC YOUR STRATEGY MUST BEAT (memorize this)

- Cost model: 5 bps taker fee + 2 bps slippage PER SIDE = 14 bps round trip
  at the pack's own block; the gate also tests 11 bps (repo) and 22 bps (2x).
  A strategy must remain profitable at 22 bps round trip to pass G8.
- The gates only detect an edge of ~20-30 bps PER TRADE net of costs. A book
  whose typical win is 5-15 bps is indistinguishable from noise at any sample
  size you can generate in two years of data. DISCARD any design whose
  expected per-trade net edge is below ~20 bps.
- Practical consequence: on 1m-5m bars, fixed targets of 0.1%-0.5% are DEAD
  (the round trip alone is 14 bps and the noise floor eats the rest). Targets
  must be structural (multi-ATR follow-through, gap fills, event moves) or the
  timeframe must be high enough that a typical trade spans 15+ bps of edge.
- Sample size: the gates require >= 100 closed trades over the history (and
  the out-of-sample half alone needs >= 30). On 15m bars two years holds
  ~70,000 bars — design entries that fire roughly 100-600 times, not 5 and
  not 20,000.
- Concentration: if you remove the best 5% of trades, the best month, AND the
  best ISO week, the book must still be net positive. Designs that ride one
  or two big trends fail this. Many small independent wins beat a few heroes.
- Stability: at least 70% of five chronological folds must be profitable
  (PF > 1), at least 60% of months green with the worst month no worse than
  -15%, and the bootstrapped 95% lower bound of per-trade expectancy must be
  ABOVE ZERO — with 100+ trades that means the MEAN per-trade net return must
  exceed roughly 2 standard deviations divided by sqrt(n). For 100 trades
  with 1% per-trade variance that is a mean edge of ~20 bps, again.
- Drawdown: P95 bootstrapped max drawdown must stay under 35% at full-equity
  compounding. Stop distances and sizing must make ruin impossible.
- Multiple testing: ~1,500 strategies have already been tried in this
  pipeline. Your strategy is guilty of selection bias until proven otherwise;
  prefer designs with a STRUCTURAL reason for the edge (mechanism, not
  pattern-fit).

## 3. ALREADY KILLED — do not regenerate these, they are measured dead

Vanilla trend crosses at any timeframe: EMA/SMA crosses (any pair of
periods), Supertrend flips, MACD line or histogram crosses, Parabolic SAR
reversals, Ichimoku cloud breakouts, Keltner/Donchian/Bollinger breakouts,
RSI(2)/RSI(14)/Stochastic/StochRSI/CCI mean reversion, VWAP fades and bounces,
Bollinger squeezes, opening-range breakouts, Asian-range breakouts, daily
pivot bounces, NR4/NR7 contraction breaks, multi-timeframe confluence stacks,
z-score pairs on crypto majors, HMA/linear-regression trend books, momentum-
ignition copies, and every 1m/3m scalping book (33 of 42 such books were
RUINED at these costs). "ADX > 25" as a filter on any of the above does not
save it. Re-combos of these primitives with new stops/targets fail on signal,
not on parameters — do not re-emit them with different constants.

## 4. THE DNA OF WHAT ALMOST SURVIVED (design toward this, with a mechanism)

The closest any book has come (measured): an ETH 5m momentum-ignition book —
a single expansion candle (body > 2x ATR, volume > 3x average) traded in its
own direction with a ~2R asymmetric target, inside a session window: net PF
1.32 on 266 trades, breakeven 14.3 bps per side, expectancy lower bound
-0.57 bps (half a basis point short). The pattern across near-misses:

- Volatility-EXPANSION triggers with follow-through (expansion candles, gap
  opens, squeeze releases) beat every oscillator and every cross.
- Asymmetric targets (2R-4R, or "no target, structural exit") beat symmetric
  1.5x-ATR/1.5x-ATR pairs, which are mathematically dead after costs.
- Session windows (UTC: London 08:00, New York 13:30) and day-count limits
  (one or two trades per day) improve every near-miss they were added to.
- Regime gates on the DAILY/HIGHER timeframe (trend day vs range day,
  expansion vs contraction) improved survival in every pack.
- Weekend/session gap fills on 1h bars repeatedly reached PF 1.2+.
- Fading funding: books that are SHORT crowded longs RECEIVE funding — a
  structural tailwind measured up to hundreds of dollars per book.
- The ONLY full pass ever recorded in this pipeline is a DELTA-NEUTRAL
  two-sided maker-style grid on one perpetual: ~87% win rate, thousands of
  tiny spread-capturing wins, concentration 2%, three calendar years green.
  The lesson: structural edge (spread capture + funding awareness) survives;
  directional edge on bars barely does.

## 5. ARCHETYPES TO GENERATE ACROSS (produce 2-4 candidates per archetype,
   not 20 variations of one)

A. Volatility-expansion continuation: expansion events traded for multi-ATR
   follow-through on 15m-1h, gated by a higher-timeframe regime, asymmetric
   targets, one trade per window.
B. Delta-neutral / maker-style structures on a perpetual: two-sided grids,
   hedge books, basis or funding-aware structures where the edge is spread
   capture and/or funding receipt, not direction. Declare the maker-fill
   assumption honestly (fills require trade-through, not touch).
C. Event and session structure: weekend gaps, session opens, funding-
   settlement behavior, month/quarter boundaries — repeatable calendar or
   microstructure events with a mechanism, on 1h bars.
D. Cross-sectional rotation: rank the 7 perps by a trailing metric (momentum,
   volatility, funding) and hold a spread or rotation with explicit rebalance
   rules — the pack never tested this family.
E. Funding-aware carry: structures whose expected funding receipt is part of
   the edge, hedged so the price risk is not the bet.

For each candidate, name the MECHANISM in one sentence (who is on the other
side of the trade and why do they lose). A strategy without a mechanism is a
pattern-fit and will be treated as noise.

## 6. OUTPUT FORMAT (strict — the pipeline ingests exactly this)

Number every strategy. For each, output:

    N. Market: <SYMBOLUSDT or SPCX> · TF: <1m|3m|5m|15m|30m|1h|4h|1d>
    Style: <trend|reversion|breakout|scalp|day|carry|neutral|rotation>
    Entry: <exact rule on a CLOSED bar; every threshold a number; both
            directions unless declared long-only>
    Exit: <exact stop level AND target level, or the explicit exit rule if
           there is no fixed target; "trailing: ON" only if you define the
           trailing rule numerically>
    Filters: <every filter with its number; sessions in UTC hh:mm>
    Trades/2y estimate: <your honest count — must be 100-600>
    Expected net edge/trade: <your honest bps estimate AFTER 14 bps round
            trip — must be >= 20>
    Mechanism: <one sentence: who loses money to this trade and why>
    Notes: <declared readings for anything ambiguous — the pipeline audits
            every ambiguity and guesses conservatively>

## 7. SELF-CHECK BEFORE EMITTING (run every candidate through this; discard
   on any NO)

1. Does it need data that does not exist in section 1? NO -> discard.
2. Is its family in section 3, or a re-combination of killed primitives with
   new constants? -> discard.
3. Is the typical winner smaller than ~20 bps net? -> discard.
4. Would it plausibly fire 100-600 times in two years on its timeframe?
   (a 4h book rarely reaches 100 — prefer 15m-1h for this reason) -> check.
5. Are BOTH directions defined, or is long-only declared with a reason?
6. Is every number explicit (periods, multipliers, session times, caps)?
   Ambiguity is resolved against you by the auditor.
7. Could the best 5% of its trades be removed and it still be positive?
   Designs with "one big winner" mechanics -> discard.
8. Is the mechanism stated (section 5) and does it survive the sentence
   "the counterparty is X, who pays because Y"?

## 8. HONESTY RULES

- Do not attach example results, Sharpe numbers, or claims — generated
  numbers are treated as fabrication by the pipeline.
- Prefer 12 excellent candidates over 50 weak ones. The pipeline will run
  every one and publish every verdict, including the kills.
- If a candidate only works with a parameter you picked by trying values,
  say so in Notes — the pipeline will test the neighborhood and kill it.
- Declare data fears (short history, thin books) in Notes rather than
  pretending they away.
