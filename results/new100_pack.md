# NEW-100 — one hundred new strategy candidates, generated under STRATEGY_GENERATOR_PROMPT v1.0

Date: 2026-11-20. Generated from the measured evidence of this repository
(STRATEGY_GENERATOR_PROMPT.md contract, GATES_AND_RULES.md battery, the
top-100 ranking's survivor DNA, and every postmortem in AGENTS.md/STATUS.md).
These are CANDIDATES, not results. Nothing here is a claim of performance:
every number a strategy produces comes from its artifact or does not exist
(REGLA 0). The screening campaign is pre-registered in
`results/new100_pre_registration.md`.

Format per STRATEGY_GENERATOR_PROMPT section 6. Family codes:
F1 expansion continuation · F2 neutral/maker spread capture (1m-resolved
fills declared) · F3 event/session/calendar · F4 cross-sectional rotation ·
F5 funding-aware carry · F6 volatility-regime adaptive · F7 equities 1d
(SPY/QQQ via the repo's Alpaca 1d pipeline, data_dir override — an extension
of the generator contract's section 1, declared in the pre-registration).

Perp data: Binance USD-M taker klines 1m/5m/15m/1h; funding at the real
settlement instants (JUP 4h cadence declared); FUNDING_MANIFEST governs
which symbols are funding-covered. Equities: Alpaca 1d SPY/QQQ hashed CSVs.

---

## F1 — Volatility-expansion continuation (N-001..N-018)

N-001. Market: ETHUSDT · TF: 15m
Style: trend
Entry: bar body >= 2.0 x ATR(14) AND volume >= 2.5 x SMA(volume,20) AND close in top/bottom 25% of bar range; direction = candle direction; 4h regime gate: close on same side of 4h EMA(50) as trade direction; one position at a time; max one trade per 4h window.
Exit: stop = 1.2 x ATR(14) at entry bar close; target = 3.0R; opposite 15m expansion candle closes the position early.
Filters: sessions UTC 07:00-17:00 only (London + NY); skip funding-settlement bars.
Trades/2y estimate: ~260
Expected net edge/trade: 30 bps
Mechanism: liquidity consumers lift thin post-expansion offers/bids because market makers widen spreads right after the impulse; follow-through pays the widened spread.
Notes: ATR on 15m bars, Wilder.

N-002. Market: BTCUSDT · TF: 15m
Style: trend
Entry: body >= 2.0 x ATR(14) AND volume >= 2.5 x avg20 AND close in extreme 25%; direction = candle; 1d regime: 1d close > 1d SMA(50) for longs, < for shorts; one trade per 4h window.
Exit: stop 1.3 x ATR(14); target 2.5R.
Filters: UTC 13:00-21:00 (NY) only.
Trades/2y estimate: ~210
Expected net edge/trade: 28 bps
Mechanism: US-session flow chases confirmed impulses on the deepest book; late-session retail stops feed the second leg.
Notes: —

N-003. Market: SOLUSDT · TF: 15m
Style: trend
Entry: body >= 1.8 x ATR(14) AND volume >= 2.0 x avg20; direction = candle; 4h EMA(50) regime gate.
Exit: stop 1.2 x ATR(14); NO fixed target — exit on first 15m close across the 4h EMA(21) or stop.
Filters: UTC 00:00-24:00; one trade per 6h window.
Trades/2y estimate: ~300
Expected net edge/trade: 25 bps
Mechanism: structural exit lets the rare impulse run several ATRs while the stop caps losers; the counterparty is the next consolidation's breakout sellers who re-enter late.
Notes: declared asymmetric, no target.

N-004. Market: HYPEUSDT · TF: 15m
Style: trend
Entry: body >= 2.0 x ATR(14) AND volume >= 3.0 x avg20 (retail-heavy tape); direction = candle; max one trade per day.
Exit: stop 1.5 x ATR(14); target 2.0R.
Filters: UTC 07:00-17:00.
Trades/2y estimate: ~180
Expected net edge/trade: 35 bps
Mechanism: HYPE's retail-dominated flow over-trades impulse bars and pays spread+slippage twice; the second leg reclaims it.
Notes: shorter history (~1y) declared; n check happens in the battery.

N-005. Market: XRPUSDT · TF: 1h
Style: trend
Entry: 1h body >= 1.5 x ATR(14) AND volume >= 2.0 x avg20; direction = candle; 1d SMA(50) regime gate.
Exit: stop 1.2 x ATR(14); target 3.0R.
Filters: one trade per 8h window.
Trades/2y estimate: ~160
Expected net edge/trade: 26 bps
Mechanism: 1h impulses on XRP follow through because market-maker inventory rebalancing spans several bars.
Notes: —

N-006. Market: BTCUSDT · TF: 1h
Style: breakout
Entry: bar open > prior bar high + 0.25 x ATR(14) (gap-up) -> long; open < prior bar low - 0.25 x ATR(14) -> short; direction = gap direction; 1d regime gate same side.
Exit: stop = open - 1.0 x ATR(14) for longs (mirrored shorts); target 2.0R.
Filters: one trade per day.
Trades/2y estimate: ~140
Expected net edge/trade: 30 bps
Mechanism: overnight information gaps reprice slowly on perps because funding-aware holders adjust position by market order across hours.
Notes: intra-1h gaps, not weekend gaps.

N-007. Market: ETHUSDT · TF: 1h
Style: breakout
Entry: gap-open continuation as N-006 with gap threshold 0.3 x ATR(14); 1d regime gate.
Exit: stop 1.1 x ATR(14) from open; target 2.5R.
Filters: one trade per day.
Trades/2y estimate: ~130
Expected net edge/trade: 28 bps
Mechanism: as N-006; ETH holders are more funding-sensitive so gap adjustment is slower.
Notes: —

N-008. Market: SOLUSDT · TF: 15m
Style: breakout
Entry: 20-bar range percentile < 20 for >= 6 bars, then close beyond that range; direction = breakout; 4h EMA(50) regime gate.
Exit: stop 1.3 x ATR(14); target 2.0R.
Filters: UTC 07:00-17:00; one trade per 4h window.
Trades/2y estimate: ~240
Expected net edge/trade: 26 bps
Mechanism: range contraction = resting-stop accumulation; the release fills the stops of the squeezed side who then must re-enter at worse prices.
Notes: this is squeeze RELEASE with follow-through, not squeeze reversion.

N-009. Market: BTCUSDT · TF: 1h
Style: breakout
Entry: 30-bar range percentile < 20 for >= 8 bars, then close beyond range; 1d regime gate.
Exit: stop 1.3 x ATR(14); target 3.0R.
Filters: one trade per day.
Trades/2y estimate: ~120
Expected net edge/trade: 28 bps
Mechanism: as N-008 on the deeper 1h book.
Notes: —

N-010. Market: ETHUSDT · TF: 15m
Style: reversion
Entry: close breaks 20-bar high by >= 0.1 x ATR, then within 3 bars closes back below the 20-bar-high level -> short; mirrored for lows -> long; session UTC 07:00-17:00.
Exit: stop 1.2 x ATR(14) beyond the failed extreme; target 2.0R.
Filters: one trade per 6h window.
Trades/2y estimate: ~200
Expected net edge/trade: 24 bps
Mechanism: the failed breakout's longs (stopped-out liquidity grab buyers) exit at market over the next bars.
Notes: DECLARED ADJACENT to the killed failed-breakout family (QS-029): differs by the re-cross timing window, session gate and asymmetric target; judged on its own artifacts per REGLA 1.

N-011. Market: JUPUSDT · TF: 15m
Style: trend
Entry: body >= 2.0 x ATR(14) AND taker-buy fraction of volume >= 0.60 (longs) or <= 0.40 (shorts) AND volume >= 2.5 x avg20; direction = candle.
Exit: stop 1.4 x ATR(14); target 2.0R.
Filters: one trade per 6h window.
Trades/2y estimate: ~200
Expected net edge/trade: 30 bps
Mechanism: one-sided aggressive flow on a retail perp continues as latecomers chase the visible tape.
Notes: taker columns exist in the taker files; JUP funding 4h cadence.

N-012. Market: SUIUSDT · TF: 15m
Style: trend
Entry: body >= 2.0 x ATR(14) AND volume >= 2.5 x avg20; direction = candle; 4h EMA(50) regime.
Exit: stop 1.3 x ATR(14); target 2.0R.
Filters: UTC 07:00-17:00; one trade per 4h window.
Trades/2y estimate: ~230
Expected net edge/trade: 28 bps
Mechanism: as N-001 on a thinner book where spread widening after impulses is larger.
Notes: —

N-013. Market: ETHUSDT · TF: 1h
Style: trend (short-biased filter)
Entry: SHORT only when funding(8h) > +0.03%: 1h body <= -1.5 x ATR(14) (bearish expansion) AND volume >= 2.0 x avg20; LONG only when funding(8h) < -0.03% with bullish expansion.
Exit: stop 1.3 x ATR(14); target 2.5R.
Filters: one trade per day.
Trades/2y estimate: ~150
Expected net edge/trade: 32 bps
Mechanism: crowded paid side unwinds into the expansion; the trader also sits on the receiving side of funding.
Notes: bridge family to F5.

N-014. Market: BTCUSDT · TF: 15m
Style: trend
Entry: TWO consecutive expansion candles (each body >= 1.5 x ATR(14), vol >= 2.0 x avg20) in the same direction; enter on the second bar's close signal; 1d regime gate.
Exit: stop 1.5 x ATR(14) from entry; target 3.0R.
Filters: one trade per day.
Trades/2y estimate: ~180
Expected net edge/trade: 27 bps
Mechanism: two impulses confirm institutional participation rather than one print; late retail provides the follow-through.
Notes: —

N-015. Market: SOLUSDT · TF: 1h
Style: breakout
Entry: close makes a 20-day high (1h close above rolling max of last 480 1h bars) with 1h body >= 1.2 x ATR(14); long only at new highs; mirrored 20-day lows short.
Exit: stop 1.5 x ATR(14); target 2.5R.
Filters: one trade per 2 days.
Trades/2y estimate: ~110
Expected net edge/trade: 30 bps
Mechanism: 20-day-high entries capture the only moments short-side liquidity is thin enough for multi-ATR follow-through.
Notes: —

N-016. Market: XRPUSDT · TF: 15m
Style: trend
Entry: expansion as N-001 thresholds BUT skip if volume > 8.0 x avg20 (climax exhaustion); direction = candle; 4h regime gate.
Exit: stop 1.2 x ATR(14); target 2.5R.
Filters: UTC 07:00-17:00.
Trades/2y estimate: ~220
Expected net edge/trade: 26 bps
Mechanism: the climax filter removes the prints where the OTHER side of the book is the one being paid (exhaustion), keeping only inventory-rebalance follow-through.
Notes: —

N-017. Market: BTCUSDT · TF: 15m
Style: trend
Entry: expansion candle (body >= 2.0 x ATR, vol >= 2.5 x avg20) whose bar opens within the UTC 13:30-14:30 window; direction = candle.
Exit: stop 1.2 x ATR(14); target 2.0R.
Filters: one trade per day; no other session.
Trades/2y estimate: ~130
Expected net edge/trade: 30 bps
Mechanism: US data-window impulses reprice after the print; the counterparty is pre-print positioning unwinding at market.
Notes: —

N-018. Market: ETHUSDT · TF: 15m
Style: trend
Entry: expansion candle opening within UTC 08:00-09:00 (London); direction = candle.
Exit: stop 1.2 x ATR(14); target 2.0R.
Filters: one trade per day.
Trades/2y estimate: ~120
Expected net edge/trade: 28 bps
Mechanism: London opens reprice the Asian accumulation; the counterparty is Asian-session inventory sold into the open.
Notes: —

## F2 — Neutral / maker spread capture, 1m-resolved fills (N-019..N-030)

ALL F2 books declare fill_model = 1m_resolved: entries and exits are resting
maker orders resolved on the 1m tape (trade-through required, not touch),
inheriting the repo's fill-model rule; the screening run resolves them on
the 1m klines (certification on real aggTrades is a later gate).

N-019. Market: XRPUSDT · TF: 15m (fills on 1m)
Style: neutral
Entry: two-sided maker grid, spacing 0.20%; buy limit one spacing below last grid fill, sell limit one spacing above; grid re-centers on the 15m close every bar; inventory cap +/- 3 units.
Exit: opposite-side grid fills (each pair nets one spacing); inventory forced-flat at 0.5% slippage if cap breached 3 times in 1h.
Filters: pause new buys when funding > +0.10% (short bias), pause sells when funding < -0.10%.
Trades/2y estimate: ~4000 (pairs)
Expected net edge/trade: 14 bps gross spacing minus 2 bps maker RT = ~12 bps net per pair, funding tailwind extra
Mechanism: retail takers and liquidation cascades cross the spread; the grid is paid the spread for immediacy.
Notes: XRP neutral family adjacency DECLARED (the 15m-book kill motivates the 1m-resolved fills).

N-020. Market: XRPUSDT · TF: 15m (fills on 1m)
Style: neutral
Entry: grid spacing = 0.8 x ATR(15m, 96 bars), re-scaled daily; two-sided; cap +/- 2 units.
Exit: opposite fills; inventory flat on day roll.
Filters: pause when 15m ATR > 2 x its 30d median (regime breaker).
Trades/2y estimate: ~3000
Expected net edge/trade: ~13 bps
Mechanism: volatility-scaled spacing pays the spread where spread income per unit risk is highest.
Notes: —

N-021. Market: SUIUSDT · TF: 15m (fills on 1m)
Style: neutral
Entry: two-sided grid 0.25% spacing, cap +/- 2.
Exit: opposite fills; day-roll flat.
Filters: pause when funding crosses +/-0.08%.
Trades/2y estimate: ~2600
Expected net edge/trade: ~14 bps
Mechanism: thinner book, wider effective spread; takers pay more.
Notes: —

N-022. Market: HYPEUSDT · TF: 15m (fills on 1m)
Style: neutral
Entry: two-sided grid 0.35% spacing, cap +/- 2.
Exit: opposite fills.
Filters: pause when 15m ATR > 2.5 x 30d median.
Trades/2y estimate: ~1800
Expected net edge/trade: ~16 bps
Mechanism: HYPE retail takers pay the widest spreads in the universe.
Notes: —

N-023. Market: XRPUSDT · TF: 15m (fills on 1m)
Style: reversion
Entry: session VWAP (rolling 96 x 15m) +/- 1.5 sigma bands; maker limit at the band; both sides.
Exit: maker take-profit at VWAP; stop via opposite band + 0.5 sigma; cap 4 pairs/day.
Filters: skip when ATR percentile > 90.
Trades/2y estimate: ~1600
Expected net edge/trade: ~15 bps
Mechanism: systematic liquidations and stop runs push price one band-sigma past fair value; providers are paid to absorb.
Notes: —

N-024. Market: ETHUSDT · TF: 5m (fills on 1m)
Style: neutral
Entry: two-sided grid 0.15% spacing, cap +/- 4 units.
Exit: opposite fills.
Filters: pause 00:00-01:00 UTC (funding settlement window).
Trades/2y estimate: ~5000
Expected net edge/trade: ~10 bps
Mechanism: deepest book, tightest viable spread; volume compensates.
Notes: high turnover makes it cost-sensitive by design — the battery will judge.

N-025. Market: JUPUSDT · TF: 15m (fills on 1m)
Style: neutral
Entry: two-sided grid 0.30% spacing, cap +/- 2.
Exit: opposite fills.
Filters: funding 4h cadence declared; pause on settlement bars.
Trades/2y estimate: ~2000
Expected net edge/trade: ~14 bps
Mechanism: retail perp, wide spread, frequent liquidation wicks.
Notes: —

N-026. Market: ARBUSDT · TF: 15m (fills on 1m)
Style: neutral
Entry: two-sided grid 0.25% spacing, cap +/- 2.
Exit: opposite fills.
Filters: pause when funding > +/-0.08%.
Trades/2y estimate: ~2200
Expected net edge/trade: ~13 bps
Mechanism: as N-021.
Notes: —

N-027. Market: XRPUSDT · TF: 15m (fills on 1m)
Style: neutral (funding-biased)
Entry: grid as N-019 but side weights 70/30 toward the RECEIVING side of current funding (short-heavy when funding positive).
Exit: opposite fills; bias re-set each 8h settlement.
Filters: as N-019.
Trades/2y estimate: ~3500
Expected net edge/trade: ~13 bps spread + funding receipt
Mechanism: spread capture PLUS sitting on the paid side; crowded-side takers pay twice.
Notes: —

N-028. Market: BTCUSDT · TF: 5m (fills on 1m)
Style: neutral
Entry: tight grid 0.10% spacing, cap +/- 4, day inventory flat.
Exit: opposite fills.
Filters: pause when 5m ATR > 2.5 x 30d median.
Trades/2y estimate: ~6000
Expected net edge/trade: ~9 bps
Mechanism: the only book where a 0.10% spacing is credible; volume is the edge.
Notes: —

N-029. Market: SUIUSDT · TF: 15m (fills on 1m)
Style: neutral
Entry: grid 0.22% spacing with volatility circuit-breaker (no new orders while 15m ATR > 2 x 30d median; existing pairs left to resolve).
Exit: opposite fills.
Filters: as stated.
Trades/2y estimate: ~2400
Expected net edge/trade: ~14 bps
Mechanism: keeps the book out of the liquidation-cascade minutes that are the grid's only true risk.
Notes: —

N-030. Market: XRPUSDT · TF: 15m (fills on 1m)
Style: neutral
Entry: maker entries both sides at 0.20% spacing; NO hard stop — exit only via opposite side or inventory cap (risk device = cap, not stop).
Exit: opposite fills; cap-forced flat at market.
Filters: cap +/- 3; pause on funding extremes.
Trades/2y estimate: ~3800
Expected net edge/trade: ~13 bps
Mechanism: pure spread book; the inventory cap is the declared risk device replacing the stop.
Notes: risk-device swap declared; battery measures the tail.

## F3 — Event / session / calendar structure (N-031..N-048)

N-031. Market: BTCUSDT · TF: 1h
Style: reversion
Entry: weekend gap = Monday 00:00 UTC open vs Saturday 00:00 UTC close; |gap| >= 1.0 x ATR(1d,20) and <= 2.0 x ATR(1d,20); fade the gap (trade toward Saturday close).
Exit: stop 1.5 x ATR(1d,20) from entry; target = Saturday close level or 48h time stop, whichever first.
Filters: Monday UTC 00:00-12:00 entry window only; one trade.
Trades/2y estimate: ~95
Expected net edge/trade: 35 bps
Mechanism: weekend illiquidity over-extends price; Monday institutional flow re-prices toward fair value.
Notes: S46 adjacency declared; band excludes the big-gap tail this book cannot fade.

N-032. Market: ETHUSDT · TF: 1h
Style: reversion
Entry: as N-031, gap band 1.0-2.2 x ATR(1d,20).
Exit: stop 1.6 x ATR; target Saturday close or 48h stop.
Filters: Monday entry window.
Trades/2y estimate: ~90
Expected net edge/trade: 32 bps
Mechanism: as N-031; ETH weekend books are thinner so the over-extension is larger.
Notes: —

N-033. Market: BTCUSDT · TF: 1h
Style: breakout
Entry: weekend gap >= 2.0 x ATR(1d,20): CONTINUE in gap direction (the opposite hypothesis of N-031 — big gaps are information, small gaps are noise).
Exit: stop 1.2 x ATR(1d,20) from entry; target 2.0R.
Filters: Monday window; one trade.
Trades/2y estimate: ~40
Expected net edge/trade: 45 bps
Mechanism: weekend news that moves BTC 2+ daily-ATRs repriced institutions' books; Monday flow continues the adjustment.
Notes: low n declared; the battery's sample floor will judge.

N-034. Market: BTCUSDT · TF: 1h
Style: carry
Entry: when funding(8h) < -0.01% (shorts crowded, longs receive): long 30 min before settlement, exit 2h after; vol-scaled 0.5% risk.
Exit: fixed 2.5h hold.
Filters: only settlements with negative funding.
Trades/2y estimate: ~330
Expected net edge/trade: 22 bps (mostly funding receipt)
Mechanism: crowded shorts pay longs at settlement; the pre-settlement unwind of late short-covering drifts price up.
Notes: —

N-035. Market: ETHUSDT · TF: 1h
Style: carry
Entry: funding(8h) > +0.02%: SHORT 30 min before settlement, exit 2h after.
Exit: fixed 2.5h hold.
Filters: positive-funding settlements only.
Trades/2y estimate: ~300
Expected net edge/trade: 22 bps
Mechanism: mirror of N-034; crowded longs pay shorts.
Notes: —

N-036. Market: BTCUSDT · TF: 15m
Style: breakout
Entry: first 30-minute range after 08:00 UTC; close beyond the range with body >= 0.8 x ATR(14) -> follow; 1d regime gate.
Exit: stop = opposite side of the 30m range; target 2.0R.
Filters: London only; one trade/day.
Trades/2y estimate: ~180
Expected net edge/trade: 27 bps
Mechanism: European desks reprice overnight information through the Asian range; passive Asian-side stops feed the move.
Notes: —

N-037. Market: ETHUSDT · TF: 15m
Style: breakout
Entry: first 30m range after 13:30 UTC broken with body >= 0.8 x ATR(14); 1d regime gate.
Exit: stop opposite range side; target 2.0R.
Filters: NY only; one trade/day.
Trades/2y estimate: ~170
Expected net edge/trade: 27 bps
Mechanism: US macro window repricing; as N-036.
Notes: —

N-038. Market: BTCUSDT · TF: 15m
Style: reversion
Entry: London first-hour extreme (price > 1.5 x ATR(14) above the 08:00 VWAP) faded BACK toward VWAP only when the 1d regime is FLAT (|1d close - 1d SMA(20)| < 0.5 x ATR(1d)).
Exit: stop 1.2 x ATR(14) beyond the extreme; target VWAP touch or 2R whichever first.
Filters: 09:00-11:00 UTC; one trade/day.
Trades/2y estimate: ~150
Expected net edge/trade: 25 bps
Mechanism: in range regimes the London open's liquidity grab is paid for by its own chasers.
Notes: —

N-039. Market: BTCUSDT · TF: 1h
Style: carry
Entry: long the close of the last day of the month, exit the close of the second day of the new month; size = 0.5% risk to a 2 x ATR(1d) stop.
Exit: time exit (2 trading days) or stop.
Filters: month boundaries only.
Trades/2y estimate: ~48
Expected net edge/trade: 40 bps
Mechanism: month-end rebalancing demand for the benchmark asset; the counterparty is the fund that must trade on the calendar, not on price.
Notes: low n declared; battery judges the sample floor.

N-040. Market: ETHUSDT · TF: 1h
Style: carry
Entry: when funding(8h) > +0.06% for 3 consecutive settlements: SHORT, hold while funding stays > +0.03%.
Exit: funding-condition exit or 2 x ATR(1d) stop.
Filters: one position.
Trades/2y estimate: ~55
Expected net edge/trade: 50 bps (carry-heavy)
Mechanism: extreme crowding pays the short AND precedes long liquidations; the position is paid to wait for it.
Notes: low n; concentration check matters.

N-041. Market: BTCUSDT · TF: 1h
Style: trend
Entry: Monday 01:00-06:00 UTC: if the Monday open gaps/trades beyond Saturday close in either direction with 1h body >= 1.0 x ATR(14), follow.
Exit: stop 1.3 x ATR(14); target 2.0R.
Filters: Monday only.
Trades/2y estimate: ~85
Expected net edge/trade: 30 bps
Mechanism: weekend accumulation unwinds into Monday Asia; the continuation is the adjustment trade.
Notes: —

N-042. Market: ETHUSDT · TF: 1h
Style: carry
Entry: Friday 20:00-24:00 UTC: short when the week is up >= +5% (de-risking into weekend tail risk).
Exit: Monday 08:00 UTC time exit or 1.5 x ATR(1d) stop.
Filters: Fridays only.
Trades/2y estimate: ~90
Expected net edge/trade: 28 bps
Mechanism: weekend gap-risk premium: holders pay (funding + spread) to keep long tail exposure over the weekend; the seller collects.
Notes: —

N-043. Market: JUPUSDT · TF: 1h
Style: carry
Entry: JUP settles every 4h; when funding > 0, short the bar BEFORE settlement, exit the bar after (the 4h cadence doubles the settlement count vs 8h names).
Exit: fixed 2-bar hold.
Filters: positive settlements only.
Trades/2y estimate: ~700 (2y x 4380 settlements/4h x hit rate)
Expected net edge/trade: 15-20 bps
Mechanism: the 4h cadence front-runs the 8h names' settlement flows; crowded longs pay four times a day on the most retail-heavy perp.
Notes: edge floor concern declared — battery decides if it clears.

N-044. Market: BTCUSDT · TF: 1h
Style: reversion
Entry: last 2 hours of the UTC day: if price > daily VWAP + 2.0 x sigma(1h) -> short toward VWAP; mirrored long.
Exit: VWAP touch (target) or 1.2 x ATR(14) stop.
Filters: 22:00-00:00 UTC only.
Trades/2y estimate: ~160
Expected net edge/trade: 24 bps
Mechanism: end-of-day inventory flattening pulls price back to the day's transacted mean; the stretch is the day's liquidity taker being paid back.
Notes: —

N-045. Market: ETHUSDT · TF: 15m
Style: reversion
Entry: session VWAP stretch >= 2.0 sigma AND 1d regime flat (as N-038's filter); fade toward session VWAP.
Exit: VWAP touch or stop 1.3 x ATR(14); 2R cap via time stop 6 bars.
Filters: UTC 07:00-20:00; 2 trades/day max.
Trades/2y estimate: ~260
Expected net edge/trade: 24 bps
Mechanism: systematic liquidation clusters at band extremes; providers absorb at sigma prices.
Notes: VWAP-fade adjacency DECLARED: differs by sigma threshold, regime gate, asymmetric stop and day caps.

N-046. Market: XRPUSDT · TF: 1h
Style: breakout
Entry: Asian range (00:00-07:00 UTC) breakout on the 07:00-09:00 bars with volume >= 1.5 x avg20; 1d regime gate.
Exit: stop opposite Asian range side; target 2.0R.
Filters: one trade/day.
Trades/2y estimate: ~140
Expected net edge/trade: 26 bps
Mechanism: London grabs the Asian accumulation's stops; the follow-through is the repositioning.
Notes: ORB adjacency declared (session-specific, volume-confirmed, regime-gated).

N-047. Market: SOLUSDT · TF: 1h
Style: carry
Entry: long Friday 22:00 UTC close; exit Monday 07:00 UTC (weekend hold) sized 0.3% risk to a 3 x ATR(1d) stop; only when funding(8h) < +0.02% (not paying to hold).
Exit: Monday time exit or stop.
Filters: weekends only; funding gate.
Trades/2y estimate: ~100
Expected net edge/trade: 25 bps
Mechanism: weekend short-side squeeze: market makers pull liquidity Fri-Sun; marginal demand moves price more per dollar.
Notes: —

N-048. Market: BTCUSDT · TF: 1m (fills on 1m)
Style: neutral
Entry: resting maker orders at the nearest 1000-USDT price levels both sides; re-pegged every 15m close to the current level grid; cap +/- 2 units.
Exit: opposite level fills; day flat.
Filters: pause when 1m ATR > 3 x 30d median.
Trades/2y estimate: ~4500
Expected net edge/trade: ~10 bps
Mechanism: retail limit-and-stop placement clusters at round numbers; the maker is paid for the liquidity at the cluster.
Notes: round-number microstructure; 1m fill resolution declared.

## F4 — Cross-sectional rotation and spreads (N-049..N-068)

Universe: the 8 funding-covered perps (BTC ETH SOL XRP SUI ARB JUP HYPE).
All rank books: decision on the rebalance bar's close, execution next open,
vol-scaled sizing (each leg 10% vol-target unless stated), 11 bps RT per
leg, funding at real settlements, weekly rebalance unless stated, hysteresis
band 2 ranks (hold until the name leaves top/bottom 4).

N-049. Market: 8-perp bundle · TF: 1h
Style: rotation
Entry: score = 21d return - 10 x avg funding(7d); long top-2, short bottom-2, weekly rebalance, vol-scaled.
Exit: rank exit with hysteresis; per-leg stop 3 x ATR(1d).
Filters: gross exposure <= 2x equity.
Trades/2y estimate: ~230 leg-trades
Expected net edge/trade: 30 bps
Mechanism: momentum crowded by funding decays; the score buys momentum the crowd is NOT paying for and sells the crowding itself.
Notes: —

N-050. Market: 8-perp · TF: 1h
Style: rotation
Entry: pure 21d momentum, long top-3 equal-weight, no short leg, weekly.
Exit: rank exit (top-4 hold band); portfolio stop 10% from high-water.
Filters: long-only declared (crypto perp long-beta is the deliverable).
Trades/2y estimate: ~150
Expected net edge/trade: 25 bps
Mechanism: perp momentum persists into the next week because position adjustments are funding- and margin-constrained, not price-targeted.
Notes: —

N-051. Market: 8-perp · TF: 1h
Style: rotation
Entry: long the 3 lowest 21d realized-vol names, hedged 50% short BTC.
Exit: weekly rank exit; BTC hedge re-sized weekly.
Filters: —
Trades/2y estimate: ~160
Expected net edge/trade: 22 bps
Mechanism: low-vol crypto names carry less liquidation tail risk; the market over-pays beta, not stability, and the hedge strips the beta.
Notes: LOWVOL-family adjacency DECLARED (xsf-1 killed un-hedged; this is the hedged construct).

N-052. Market: 8-perp · TF: 1h
Style: rotation
Entry: long strongest 21d momentum name, short weakest, each beta-hedged 0.8 x against BTC (beta = 30d rolling).
Exit: weekly; stop when the spread moves 2 x its 30d stdev against.
Filters: dollar-neutral.
Trades/2y estimate: ~100
Expected net edge/trade: 28 bps
Mechanism: relative strength on perps is a position-flow variable, not a valuation; the spread persists because carry costs keep arbitrage capital out.
Notes: —

N-053. Market: 8-perp · TF: 1h
Style: carry
Entry: short top-2 funding, long bottom-2 funding, weekly, vol-scaled, dollar-neutral.
Exit: rank exit with hysteresis.
Filters: —
Trades/2y estimate: ~220
Expected net edge/trade: 35 bps (majority = funding receipt)
Mechanism: the crowded side pays the quiet side every 8h; the rank just sits on the receiving side of an accounting identity.
Notes: —

N-054. Market: 8-perp · TF: 1h
Style: carry
Entry: funding regime switch: where funding(3d) > funding(21d) -> short that name (crowding building), where funding(3d) < funding(21d) -> long; top/bottom 2 only; weekly.
Exit: rank/condition exit.
Filters: —
Trades/2y estimate: ~190
Expected net edge/trade: 28 bps
Mechanism: funding ACCELERATION marks crowding formation; positioning against the acceleration collects the unwind.
Notes: —

N-055. Market: 8-perp · TF: 1h
Style: rotation
Entry: long top-2 by taker-buy share of volume (21d average), short bottom-2; weekly.
Exit: rank exit.
Filters: —
Trades/2y estimate: ~210
Expected net edge/trade: 24 bps
Mechanism: persistent buy-side aggression (net taker imbalance) is informed accumulation on perps; the passive side funds it.
Notes: —

N-056. Market: 8-perp · TF: 1h
Style: rotation
Entry: long the 3 names whose 21d realized vol sits in the 50-80th percentile of the cross-section (mid-vol), skip extremes; weekly.
Exit: rank exit.
Filters: —
Trades/2y estimate: ~170
Expected net edge/trade: 22 bps
Mechanism: extreme-vol names carry liquidation tails; mid-vol names compound without the tail; the cross-section misprices the difference.
Notes: —

N-057. Market: majors-3 (BTC ETH SOL) · TF: 1h
Style: reversion
Entry: long any major whose drawdown from its 60d high exceeds -30% and whose 1d RSI(14) < 30, time-stop 14 days, 1% risk to 2 x ATR(1d).
Exit: time exit or stop or recovery to the 20d high minus 5%.
Filters: one position per name.
Trades/2y estimate: ~60
Expected net edge/trade: 45 bps
Mechanism: perp liquidation cascades overshoot fair value on majors; the forced seller is the liquidation engine, not a trader with a view.
Notes: low n + concentration risk declared.

N-058. Market: 8-perp · TF: 1h
Style: rotation
Entry: long top-2 by 21d return MINUS BTC's 21d return (relative strength), short bottom-2; weekly.
Exit: rank exit.
Filters: —
Trades/2y estimate: ~210
Expected net edge/trade: 26 bps
Mechanism: idiosyncratic strength on perps is project-specific flow (listings, unlocks); BTC-beta cannot price it away for retail books.
Notes: —

N-059. Market: 8-perp · TF: 1h
Style: rotation
Entry: median of three ranks (21d momentum, funding(7d) asc, 21d vol asc); long top-2 median, short bottom-2; weekly.
Exit: rank exit.
Filters: —
Trades/2y estimate: ~200
Expected net edge/trade: 26 bps
Mechanism: rank medians damp the single-metric noise that killed the single-factor rotation books; the mechanism is the crowding-weighted composite, not any one factor.
Notes: —

N-060. Market: 8-perp · TF: 1h
Style: reversion
Entry: among the top-4 by 30d return, long the name whose 5d return is the most negative (pullback within strength), weekly; long-only leg, 50% vol-target.
Exit: 5d return turns positive or 14-day time stop.
Filters: —
Trades/2y estimate: ~110
Expected net edge/trade: 27 bps
Mechanism: strength-family pullbacks are dip-buyers' inventory being filled at a discount; the trend provides the exit.
Notes: —

N-061. Market: 7 alts vs BTC · TF: 1h
Style: carry
Entry: every Friday 20:00 UTC: short equal-weight 7-alts basket, long BTC same notional; unwind Monday 07:00.
Exit: time exit.
Filters: weekends only.
Trades/2y estimate: ~100 (weekly pairs)
Expected net edge/trade: 30 bps
Mechanism: weekend alts bleed vs BTC (liquidity asymmetry: alt makers leave first); the spread is paid to whoever holds the BTC side over the weekend.
Notes: —

N-062. Market: 8-perp · TF: 1h
Style: carry
Entry: short the single highest-funding perp, hedged 100% long BTC, weekly, vol-scaled.
Exit: weekly; early exit when its funding < median.
Filters: —
Trades/2y estimate: ~100
Expected net edge/trade: 32 bps
Mechanism: idiosyncratic crowding is a perp-specific flow; hedging BTC strips the market leg and isolates the carry plus the crowding unwind.
Notes: —

N-063. Market: 8-perp · TF: 1h
Style: breakout
Entry: long any perp closing at a 30d high with 1d body >= 0.8 x ATR(1d); exit on a 10d-low close; sized 1% risk to 2 x ATR(1d) stop; max 3 concurrent.
Exit: as stated.
Filters: —
Trades/2y estimate: ~130
Expected net edge/trade: 30 bps
Mechanism: cross-sectional new-high breakout rotates the book INTO the name where liquidity is being added and OUT of the rest.
Notes: —

N-064. Market: SOL/ETH pair · TF: 1h
Style: reversion
Entry: 30d beta-adjusted SOL/ETH log-ratio spread; entry |z| >= 2.5 toward the mean, exit z <= 0.5; only when the 30d half-life of the spread is between 2 and 15 days.
Exit: z-exit or 4 x sigma stop.
Filters: half-life gate.
Trades/2y estimate: ~90
Expected net edge/trade: 30 bps
Mechanism: the SOL/ETH relative-value trade is crowded on the ENTRY side but the EXIT side (half-life reversion) is structural; the gate removes the dead regimes.
Notes: z-pair adjacency DECLARED (killed family; construct differs by beta adjustment, half-life gate, asymmetric exit).

N-065. Market: ETH/BTC ratio · TF: 1d
Style: trend
Entry: ratio 20d momentum > 0 AND ratio > its 50d mean -> long ratio (long ETH short BTC); mirrored short; weekly rebalance.
Exit: momentum flip or 2 x sigma(20d) stop.
Filters: —
Trades/2y estimate: ~70
Expected net edge/trade: 28 bps
Mechanism: the ETH/BTC ratio trends on risk-appetite cycles that outlast a week; funding costs on both legs are the entry hurdle, not the edge.
Notes: —

N-066. Market: HYPE vs 7 alts · TF: 1h
Style: rotation
Entry: when HYPE's 21d-momentum rank is 1 for >= 5 consecutive days: long HYPE 50%, short equal-weight 7 alts 50%; exit when rank leaves 1-2.
Exit: as stated.
Filters: —
Trades/2y estimate: ~60
Expected net edge/trade: 35 bps
Mechanism: dominance persistence in a retail-heavy name reflects flow share, not valuation; the alt short leg collects the bleed.
Notes: low n; concentration judged by the battery.

N-067. Market: 8-perp · TF: 1h
Style: rotation
Entry: when the cross-sectional dispersion of 7d returns (stdev across the 8) exceeds its 90th 60d percentile: long the top-2 momentum names; flat otherwise.
Exit: dispersion back under the 60th percentile or 10d.
Filters: regime-gated, mostly flat.
Trades/2y estimate: ~90
Expected net edge/trade: 32 bps
Mechanism: dispersion expansion = rotation regime; leaders keep getting funded while laggards are abandoned; in compressed regimes momentum dies.
Notes: —

N-068. Market: 8-perp · TF: 1h
Style: rotation
Entry: hold any name ranked 1-2 by 21d momentum for 3 consecutive weekly rebalances (persistence); long 50% vol-target; flat otherwise.
Exit: rank decay.
Filters: —
Trades/2y estimate: ~80
Expected net edge/trade: 30 bps
Mechanism: rank persistence filters one-week momentum noise; the survivor names are where multi-week flows concentrate.
Notes: —

## F5 — Funding-aware carry (N-069..N-082)

N-069. Market: 8-perp · TF: 1h
Style: carry
Entry: when a perp's avg funding(7d) > +0.05%: short it, vol-targeted 20%, hedged 50% long BTC; roll weekly.
Exit: funding < +0.02% or weekly.
Filters: —
Trades/2y estimate: ~110
Expected net edge/trade: 35 bps (carry-heavy)
Mechanism: paid to hold the crowded side's opposite while the hedge strips direction; the edge is the accounting identity, the hedge is the discipline.
Notes: —

N-070. Market: 8-perp · TF: 1h
Style: carry
Entry: funding(7d) < -0.02%: LONG that perp (longs RECEIVE), no hedge, stop 2 x ATR(1d), vol-targeted 15%.
Exit: funding > 0 or stop.
Filters: one position.
Trades/2y estimate: ~130
Expected net edge/trade: 30 bps
Mechanism: crowded shorts are squeeze fuel; being paid to hold the squeeze's fuel tank is the trade.
Notes: —

N-071. Market: 8-perp · TF: 1h
Style: carry
Entry: funding 3d-MA crosses zero: enter in the NEW receiving direction (cross to + -> short; cross to - -> long), 1h, hold 7 days or sign re-cross.
Exit: as stated.
Filters: one position per name.
Trades/2y estimate: ~180
Expected net edge/trade: 26 bps
Mechanism: funding sign flips mark crowding regime changes; the first week after a flip pays the new side while the old side unwinds.
Notes: —

N-072. Market: 8-perp · TF: 1h
Style: carry + momentum
Entry: long top-2 by 21d momentum AMONG names whose funding(7d) < +0.02% (uncrowded momentum); weekly; vol-scaled.
Exit: rank exit or funding > +0.05%.
Filters: —
Trades/2y estimate: ~120
Expected net edge/trade: 28 bps
Mechanism: momentum crowded by funding is already leveraged retail; uncrowded momentum is the same flow without the liquidation overhang.
Notes: —

N-073. Market: 8-perp · TF: 1h
Style: carry
Entry: when >= 3 of the 8 names carry funding > +0.06%: short THE highest-funding one, 1h, stop 2 x ATR(1d), vol-targeted 15%.
Exit: funding < +0.04% or stop.
Filters: one position.
Trades/2y estimate: ~85
Expected net edge/trade: 36 bps
Mechanism: cross-sectional funding extremes mark the single most-leveraged long book on the exchange; that is the liquidation queue.
Notes: —

N-074. Market: 8-perp · TF: 1h
Style: carry
Entry: funding term spread = avg(last 3 settlements) - avg(21d); |spread| > +0.03% -> position TOWARD the rich side (spread > 0 -> short); hold 3 days.
Exit: time exit or spread re-cross.
Filters: —
Trades/2y estimate: ~200
Expected net edge/trade: 25 bps
Mechanism: the term structure of funding prices crowding NOW vs crowding NORMAL; trading toward rich collects the normalization.
Notes: —

N-075. Market: BTCUSDT · TF: 1m
Style: carry
Entry: 15 min before each 8h settlement: position in the RECEIVING direction (funding > 0 -> short), exit 15 min after the settlement bar.
Exit: fixed 30-min hold.
Filters: —
Trades/2y estimate: ~1300
Expected net edge/trade: 18 bps
Mechanism: the settlement instant pays the open notional; holding exactly across it collects the payment with minimal price exposure.
Notes: edge-floor concern declared; 1m execution; the battery judges.

N-076. Market: JUPUSDT · TF: 1h
Style: carry
Entry: when JUP funding > +0.02%: short JUP 100%, hedged 60% long BTC; re-size each 4h settlement.
Exit: funding < +0.01% or weekly.
Filters: —
Trades/2y estimate: ~140
Expected net edge/trade: 33 bps
Mechanism: the 4h cadence quadruples JUP's payment frequency vs the 8h majors; the hedge strips the direction the cadence does not price.
Notes: —

N-077. Market: 8-perp · TF: 1h
Style: carry
Entry: funding > its 90th 60d percentile -> SHORT that name, exit when funding returns under its 60d median; vol-targeted 15%.
Exit: as stated.
Filters: one position per name, max 2 concurrent.
Trades/2y estimate: ~95
Expected net edge/trade: 34 bps
Mechanism: percentile regime = self-referencing crowding gauge; the exit at median makes the book a mean-reverting position on the gauge itself.
Notes: —

N-078. Market: 8-perp · TF: 1h
Style: reversion
Entry: funding < its 5th 60d percentile -> LONG that perp (shorts crowded -> squeeze fuel), entry at the settlement bar close, stop 2 x ATR(1d), target 3 x ATR(1d).
Exit: target/stop/14-day time cap.
Filters: —
Trades/2y estimate: ~90
Expected net edge/trade: 32 bps
Mechanism: crowded shorts face the same liquidation arithmetic crowded longs do, in reverse; being long the fuel tank is the squeeze trade.
Notes: —

N-079. Market: BTC + worst-funding alt · TF: 1h
Style: carry
Entry: long BTC 50% vol-target + short the CURRENT worst-funding alt 50%; re-picked weekly.
Exit: weekly roll.
Filters: —
Trades/2y estimate: ~104
Expected net edge/trade: 30 bps
Mechanism: the book holds the benchmark and rents out the crowding; the alt leg is a funding-receiving hedge, not a view.
Notes: —

N-080. Market: 8-perp · TF: 1h
Style: reversion
Entry: taker-buy fraction (1h, 24-bar mean) > 0.60 AND funding(8h) > +0.05% -> SHORT that name (retail chasing into rich funding); stop 1.5 x ATR(14); target 2.5R.
Exit: as stated.
Filters: one position; 1 trade/2 days per name.
Trades/2y estimate: ~150
Expected net edge/trade: 30 bps
Mechanism: the buyer paying taker fees INTO positive funding is the marginal leveraged long; their liquidation is the exit liquidity.
Notes: —

N-081. Market: 8-perp · TF: 1h
Style: carry
Entry: a single settlement rate > 2 x stdev(30d of rates): trade the NEXT 8h in the rate's direction (rate spike up -> short), exit after 8h.
Exit: fixed 8h hold.
Filters: one trade per name per day.
Trades/2y estimate: ~110
Expected net edge/trade: 26 bps
Mechanism: rate setters chase price (funding follows a rally with a lag); the next window continues the adjustment that set the rate.
Notes: —

N-082. Market: 8-perp · TF: 1h
Style: carry
Entry: long the lowest-funding perp vs short the highest-funding perp, dollar-neutral, weekly, vol-scaled 20% each leg.
Exit: weekly; stop when the funding spread halves.
Filters: —
Trades/2y estimate: ~104
Expected net edge/trade: 33 bps
Mechanism: the funding spread IS the crowding spread; the book is long quiet and short crowded, both of which are paid in cash every 8h.
Notes: —

## F6 — Volatility-regime adaptive (N-083..N-090)

N-083. Market: BTCUSDT · TF: 15m
Style: trend
Entry: when the 30d stdev of 15m ATR(14) crosses above its 85th 60d percentile: trade the NEXT expansion bar (body >= 1.5 x ATR) in its direction, target 2.5R.
Exit: stop 1.3 x ATR(14); target/time exit 16 bars.
Filters: one trade/4h window; regime must stay above the 60th percentile.
Trades/2y estimate: ~150
Expected net edge/trade: 28 bps
Mechanism: vol-of-vol spikes = positioning churn; churn creates follow-through that quiet regimes do not pay for.
Notes: —

N-084. Market: ETHUSDT · TF: 1h
Style: adaptive
Entry: ATR(14) percentile of the last 60d < 30: follow 20-bar breakouts (stop 1.2 x ATR, target 3R); percentile > 70: fade 20-bar extremes back to the 20-bar mid (stop 1.5 x ATR, target mid).
Exit: per regime as stated.
Filters: regime read on every bar; one trade/8h.
Trades/2y estimate: ~200
Expected net edge/trade: 26 bps
Mechanism: quiet breakouts continue (thin opposing liquidity); loud extremes mean-revert (exhaustion); the regime switch trades each state with its own physics.
Notes: —

N-085. Market: SOLUSDT · TF: 1h
Style: trend
Entry: 40-bar Donchian breakout; position size scaled by 1/ATR-percentile (quiet = full 1% risk, loud = 0.3%); exit 20-bar opposite.
Exit: as stated.
Filters: one position.
Trades/2y estimate: ~120
Expected net edge/trade: 28 bps
Mechanism: same breakout edge as every killed Donchian book, but the sizing concentrates risk where follow-through historically pays and starves it where it does not.
Notes: Donchian adjacency DECLARED — the variant is the sizing law, judged on its own artifacts.

N-086. Market: BTCUSDT · TF: 1h
Style: trend
Entry: 4h EMA(50) slope regime + 1h close crossing the 4h EMA(21): full signals; in high-vol regime (ATR pct > 70) size halves and stops double.
Exit: 4h EMA(21) cross back or adaptive stop.
Filters: —
Trades/2y estimate: ~160
Expected net edge/trade: 24 bps
Mechanism: adaptive risk keeps the trend book's expectancy positive in the regimes where fixed-risk trend books die to stop-runs.
Notes: trend-cross adjacency DECLARED (the adaptive risk law is the construct).

N-087. Market: ETHUSDT · TF: 15m
Style: breakout
Entry: 15m bar range percentile < 15 (contraction) immediately followed by a bar closing beyond the contraction's range with body >= 1.2 x ATR -> follow.
Exit: stop 1.2 x ATR(14); target 2.0R.
Filters: one trade/6h; UTC 07:00-20:00.
Trades/2y estimate: ~210
Expected net edge/trade: 27 bps
Mechanism: contraction-to-expansion transitions mark stop-pockets; the release pays whoever holds through the pocket.
Notes: —

N-088. Market: BTCUSDT · TF: 1h
Style: trend
Entry: 3 consecutive rising 1h ATR(14) readings AND the third bar is an expansion bar (body >= 1.5 x ATR): follow its direction; 1d regime gate.
Exit: stop 1.4 x ATR(14); target 2.5R.
Filters: one trade/day.
Trades/2y estimate: ~130
Expected net edge/trade: 28 bps
Mechanism: vol-cluster persistence — the third rising reading marks the cascade's institutional leg, not the retail leg.
Notes: —

N-089. Market: SOLUSDT · TF: 1h
Style: trend
Entry: BTC 1h ATR(14) jumps > 1.8 x its 20d median -> trade the NEXT expansion bar on SOL in the same direction, target 2R.
Exit: stop 1.3 x ATR(14); target/time 12 bars.
Filters: one trade/day.
Trades/2y estimate: ~140
Expected net edge/trade: 27 bps
Mechanism: BTC vol shocks spill into alts with a one-bar lag; alt makers re-price slower than BTC's.
Notes: lead-lag adjacency DECLARED (the EDGE 1m book was BTC->alts on 1m continuation; this is vol-shock gated on 1h).

N-090. Market: BTCUSDT · TF: 15m
Style: reversion
Entry: 12:00-13:30 UTC contraction fade: if the session range so far is < 0.5 x ATR(14) and price pushes > 1.2 x ATR beyond the session VWAP -> fade back to VWAP.
Exit: VWAP touch or 1.1 x ATR(14) stop.
Filters: one trade/day; skip when 1d regime trends (as N-038's flat gate).
Trades/2y estimate: ~180
Expected net edge/trade: 22 bps
Mechanism: the pre-NY quiet window has no institutional flow; pushes are retail probe orders that the 13:30 desk fades.
Notes: —

## F7 — Equities 1d, SPY/QQQ (N-091..N-100) — data_dir extension

The generator contract's section 1 predates the repo's Alpaca 1d pipeline
(data/alpaca_1d, hashed, manifest-checked). These ten books run through the
data_dir override on SPY/QQQ 1d bars, 1% risk per trade, no funding, 1.2 bps
RT (0.1 fee + 0.5 slip per side is wrong for 1d equities — declared cost
regime: 1.2 bps RT, the eqpack measured block). None of them is the killed
eqpack S-books re-emitted: the constructs below are calendar/overnight/
regime books the eqpack never ran.

N-091. Market: SPY 1d · TF: 1d
Style: carry
Entry: long at the close of the last trading day of each month; exit the close of the first trading day of the next month; 1% risk to a 3 x ATR(20d) stop.
Exit: as stated.
Filters: month boundaries.
Trades/2y estimate: ~50
Expected net edge/trade: 30 bps
Mechanism: month-end rebalancing demand for the benchmark; the counterparty trades the calendar, not the price.
Notes: —

N-092. Market: SPY 1d · TF: 1d
Style: trend
Entry: long when close within 2% of its 252d high AND SMA(50) > SMA(200); 1% risk to a 2 x ATR(20d) stop.
Exit: 20d-low close or stop.
Filters: one position.
Trades/2y estimate: ~30
Expected net edge/trade: 40 bps
Mechanism: 52w-high momentum is the best-documented equity anomaly; the counterparty is the disposition-effect seller.
Notes: low n; battery judges.

N-093. Market: QQQ 1d · TF: 1d
Style: reversion
Entry: overnight gap (open vs prior close) > 1.5 x ATR(20d): fade toward the prior close at the open; exit same-day close.
Exit: time exit (same close) or intraday-equivalent 1 x ATR(20d) stop applied at the close read.
Filters: gaps only; one trade/day.
Trades/2y estimate: ~60
Expected net edge/trade: 28 bps
Mechanism: overnight illiquidity over-extends the open; the institutional day session re-prices to fair value by the close.
Notes: bar convention declared: entry at the signal day's OPEN (next-open from the prior close signal), exit same-day close.

N-094. Market: SPY 1d · TF: 1d
Style: trend
Entry: close > open + 0.75 x ATR(20d) AND volume > 1.3 x SMA(volume,20): long at the NEXT open, exit the close of the 3rd day after.
Exit: fixed 3-day hold or stop 1.5 x ATR(20d).
Filters: one position.
Trades/2y estimate: ~70
Expected net edge/trade: 30 bps
Mechanism: follow-through days mark institutional commitment; day-2 and day-3 flow continues the accumulation.
Notes: —

N-095. Market: QQQ 1d · TF: 1d
Style: trend
Entry: 55d breakout close, 1% risk to a 2 x ATR(20d) stop.
Exit: 20d-low close or stop.
Filters: one position.
Trades/2y estimate: ~25
Expected net edge/trade: 45 bps
Mechanism: the only entries where QQQ's trend liquidity is one-sided; the counterparty is the anchor-resistant holder.
Notes: very low n declared.

N-096. Market: SPY 1d · TF: 1d
Style: carry
Entry: long the close 2 days before the third Friday (OPX week); exit the close of the third Friday.
Exit: time exit or 2 x ATR(20d) stop.
Filters: quarterly OPX weeks.
Trades/2y estimate: ~33
Expected net edge/trade: 30 bps
Mechanism: dealer gamma is long into OPX; the hedging flow buys dips that week — a mechanical, dated flow.
Notes: —

N-097. Market: SPY 1d · TF: 1d
Style: carry
Entry: long the Dec 31 close; exit the close of the 5th trading day of January.
Exit: time exit or 2 x ATR(20d) stop.
Filters: annual.
Trades/2y estimate: ~4
Expected net edge/trade: 60 bps
Mechanism: January allocations deploy in the first week; the flow is dated and one-directional.
Notes: n is tiny — the battery's sample floor will refuse it; declared honestly.

N-098. Market: QQQ 1d · TF: 1d
Style: carry
Entry: long at every close when the 20d trend is up (close > SMA(20)); exit the NEXT day's open (pure overnight leg).
Exit: next open, every day the signal holds.
Filters: —
Trades/2y estimate: ~300
Expected net edge/trade: 20 bps
Mechanism: the overnight equity premium: open-to-close is the risk leg retail takes; close-to-open is where institutional execution concentrates.
Notes: bar convention declared: daily-bar approximation of a session split; the battery measures the approximated book.

N-099. Market: SPY 1d · TF: 1d
Style: trend
Entry: 5 consecutive higher closes above SMA(20): long; size 1% risk to 2 x ATR(20d).
Exit: close < EMA(20) or stop.
Filters: one position.
Trades/2y estimate: ~35
Expected net edge/trade: 35 bps
Mechanism: streak entries mark trend days clusters; the EMA trail rides the institutional leg.
Notes: —

N-100. Market: QQQ 1d · TF: 1d
Style: regime
Entry: when SPY 20d realized vol (annualized) < 12% AND QQQ close > SMA(50): long QQQ, 1% risk; exit when vol > 20% or close < SMA(50).
Exit: as stated.
Filters: one position.
Trades/2y estimate: ~45
Expected net edge/trade: 32 bps
Mechanism: low-vol regimes carry the best momentum payoffs per unit risk (vol drag absent); the gate holds the book out of the regimes where trend dies.
Notes: —

## Honest closing note (inherited from the generator contract)

Generated numbers above are PRIORS, not results. The pipeline will run all
one hundred under the pre-registered battery and publish every verdict,
including the kills. If every one of them dies, that is the result; if some
survive, they survive the same gates that killed ~1500 predecessors.
