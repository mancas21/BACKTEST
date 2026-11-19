# scalpma20 — twenty MA-family scalp strategies (attached source): KILLED

**Verdict: zero of one hundred twenty screen cells passes the house battery.**
Every cell's profit factor is below one net of costs, every cell's net return is
negative, and the out-of-sample profit factor is below one on all but a single
degenerate small-sample cell. The screen emptied, so the neighborhood and stats
stages were not run (early stop). This is a cost-ruin kill on a signal whose
gross edge never clears the house gate even with costs switched off.

## Source of record and proof chain

- The attachment `scalp_ma_suite-20 STATEGIES-CLAUDE.py` is preserved byte-identical
  as `code/scalp_ma_source.py` (sha256 a1a72fa279ddade4609c7b9bc4bd1832242ba6327007d61677eb947c6a4b5cb4).
- The repo adapter `scalpma20` (`code/scalpma20_engine.py`, engine sha256
  7ded8133d21010c9a431273ffcdea880c816bcc8ee8a0186de407900e53ee14b) implements the
  SAME twenty signals. **Signal parity: one hundred of one hundred cells PASS**
  (`code/_scalpma20_parity.py`: long/short/exit arrays and per-strategy geometry
  identical on SUI/SOL/HYPE five-minute and SUI/BTC one-minute real bars).
- **Engine self-test: forty known answers, zero failures** (`python code/scalpma20_engine.py`):
  stop, target, short mirror, gap-through-at-open, stop-first tie, time stop,
  signal exit, flip / no-flip, cost gate, funding sign, accounting invariant,
  indicator identities, and a causality truncation test over all twenty ids.
- The accounting invariant `(cash - INIT) == sum(pnl) - funding_paid` is asserted
  INSIDE every artifact; the largest residual across the family is below one
  ten-billionth of a USDT (each artifact publishes `inv_gap_usd`).

## Declared execution regime (house standard, layered on the identical signal)

Costs are eleven bps round trip (five bps fee plus zero point five bps slippage
per side), charged on entry and exit. Funding is charged at the real settlement
instants and covers the traded window on every cell. Sizing risks one percent of
equity to the stop, notional capped at twenty-x. A declared cost gate skips a
signal whose target distance is under three-x the round trip. Warmup is three
hundred bars. Out-of-sample is a frozen seventy/thirty chronological split.

**Differences vs the attached engine are DECLARED, not port bugs:** the source
runs ten bps round trip (four fee plus one slip), charges no funding, risks half
a percent with a five-x cap, uses a two-bar cooldown and a min-sl-percent gate on
the stop distance, and fills its target as a limit without slippage. The repo
verdict uses the house regime above; the signal is proven identical.

## Screen battery (floor)

Profit factor above one point two; at least thirty closed trades; net positive;
green in at least two of three thirds; out-of-sample profit factor above one
point two AND net positive; best-five trade concentration at most one hundred
percent of net PnL; per-trade bootstrap CI lower bound above zero. All eight
must hold. Zero cells hold all eight.

## Per-cell results (every numeral backed by its cited artifact)

| label | run_id | market | id | PF | n | net % | OOS PF | zero-cost PF |
|---|---|---|---|---|---|---|---|---|
| sm20_01_HYPEUSDT_1m | `c2279445531adc99` | HYPEUSDT 1m | 01 | 0.63 | 2741 | -100.0 | 0.56 | 1.03 |
| sm20_01_HYPEUSDT_5m | `1d90c028b4f14721` | HYPEUSDT 5m | 01 | 0.74 | 6785 | -100.0 | 0.70 | 1.03 |
| sm20_01_SOLUSDT_1m | `fcd9bba0a37a1ff1` | SOLUSDT 1m | 01 | 0.52 | 704 | -95.8 | 0.49 | 0.93 |
| sm20_01_SOLUSDT_5m | `02b9558516640e3f` | SOLUSDT 5m | 01 | 0.85 | 27612 | -100.0 | 0.77 | 1.02 |
| sm20_01_SUIUSDT_1m | `eb1a87fb872c4461` | SUIUSDT 1m | 01 | 0.60 | 2166 | -100.0 | 0.56 | 0.99 |
| sm20_01_SUIUSDT_5m | `0a76f637a00c3f72` | SUIUSDT 5m | 01 | 0.67 | 16765 | -100.0 | 0.62 | 1.02 |
| sm20_02_HYPEUSDT_1m | `a4aa41e96d0f1f52` | HYPEUSDT 1m | 02 | 0.61 | 1236 | -98.8 | 0.60 | 1.03 |
| sm20_02_HYPEUSDT_5m | `5abd77ba4efcafc5` | HYPEUSDT 5m | 02 | 0.70 | 2630 | -99.9 | 0.60 | 0.96 |
| sm20_02_SOLUSDT_1m | `a2e8dc5d12c52bf5` | SOLUSDT 1m | 02 | 0.50 | 417 | -85.0 | 0.53 | 0.91 |
| sm20_02_SOLUSDT_5m | `7ee267d14d92caa9` | SOLUSDT 5m | 02 | 0.83 | 12055 | -100.0 | 0.69 | 0.98 |
| sm20_02_SUIUSDT_1m | `3185199a92d8857f` | SUIUSDT 1m | 02 | 0.54 | 1048 | -97.7 | 0.66 | 1.01 |
| sm20_02_SUIUSDT_5m | `9bac83fd29aa20ce` | SUIUSDT 5m | 02 | 0.72 | 6834 | -100.0 | 0.64 | 0.99 |
| sm20_03_HYPEUSDT_1m | `5fe7e8d151c5bf60` | HYPEUSDT 1m | 03 | 0.50 | 2599 | -100.0 | 0.41 | 0.94 |
| sm20_03_HYPEUSDT_5m | `5f69585a314760d0` | HYPEUSDT 5m | 03 | 0.66 | 5953 | -100.0 | 0.70 | 0.98 |
| sm20_03_SOLUSDT_1m | `a74a8b8b9b6556ca` | SOLUSDT 1m | 03 | 0.52 | 763 | -96.2 | 0.50 | 0.95 |
| sm20_03_SOLUSDT_5m | `022b89d74ae68e90` | SOLUSDT 5m | 03 | 0.85 | 23921 | -100.0 | 0.71 | 1.01 |
| sm20_03_SUIUSDT_1m | `7ff6bf67578bd8c3` | SUIUSDT 1m | 03 | 0.59 | 2067 | -100.0 | 0.53 | 1.01 |
| sm20_03_SUIUSDT_5m | `79688977c5a04f80` | SUIUSDT 5m | 03 | 0.63 | 14168 | -100.0 | 0.57 | 1.01 |
| sm20_04_HYPEUSDT_1m | `10bd79866b03f1d3` | HYPEUSDT 1m | 04 | 0.49 | 6512 | -100.0 | 0.54 | 0.95 |
| sm20_04_HYPEUSDT_5m | `f9cb96cc2ef98477` | HYPEUSDT 5m | 04 | 0.59 | 15408 | -100.0 | 0.75 | 0.98 |
| sm20_04_SOLUSDT_1m | `05fa7a3989f6e844` | SOLUSDT 1m | 04 | 0.51 | 1926 | -99.9 | 0.59 | 1.03 |
| sm20_04_SOLUSDT_5m | `eb2bedae892e95cd` | SOLUSDT 5m | 04 | 0.78 | 61951 | -100.0 | 0.62 | 1.00 |
| sm20_04_SUIUSDT_1m | `0320565f0f9b86df` | SUIUSDT 1m | 04 | 0.48 | 5261 | -100.0 | 0.64 | 1.04 |
| sm20_04_SUIUSDT_5m | `f2c9837ce42b3bb8` | SUIUSDT 5m | 04 | 0.68 | 37008 | -100.0 | 0.65 | 1.02 |
| sm20_05_HYPEUSDT_1m | `550413825af0c45e` | HYPEUSDT 1m | 05 | 0.43 | 5971 | -100.0 | 0.39 | 0.94 |
| sm20_05_HYPEUSDT_5m | `d7d47e6479994f37` | HYPEUSDT 5m | 05 | 0.52 | 14078 | -100.0 | 0.62 | 0.98 |
| sm20_05_SOLUSDT_1m | `ea92a8b653526184` | SOLUSDT 1m | 05 | 0.40 | 1680 | -99.9 | 0.44 | 0.98 |
| sm20_05_SOLUSDT_5m | `d33ee259b7a05b5f` | SOLUSDT 5m | 05 | 0.75 | 57719 | -100.0 | 0.65 | 1.02 |
| sm20_05_SUIUSDT_1m | `f9d45d591831d6ab` | SUIUSDT 1m | 05 | 0.49 | 4702 | -100.0 | 0.48 | 0.99 |
| sm20_05_SUIUSDT_5m | `4e325773d65d3824` | SUIUSDT 5m | 05 | 0.61 | 34333 | -100.0 | 0.44 | 1.00 |
| sm20_06_HYPEUSDT_1m | `8903efebd5d56a4a` | HYPEUSDT 1m | 06 | 0.46 | 8476 | -100.0 | 0.56 | 0.97 |
| sm20_06_HYPEUSDT_5m | `7d1f0099918775c9` | HYPEUSDT 5m | 06 | 0.57 | 19641 | -100.0 | 0.73 | 0.96 |
| sm20_06_SOLUSDT_1m | `56db4c6bb9b5c44b` | SOLUSDT 1m | 06 | 0.44 | 2485 | -100.0 | 0.55 | 1.06 |
| sm20_06_SOLUSDT_5m | `0d3419f10c45ce5d` | SOLUSDT 5m | 06 | 0.69 | 80038 | -100.0 | 0.61 | 1.00 |
| sm20_06_SUIUSDT_1m | `7bdde55391006794` | SUIUSDT 1m | 06 | 0.50 | 6828 | -100.0 | 0.64 | 1.01 |
| sm20_06_SUIUSDT_5m | `dd0307f895b8cfaf` | SUIUSDT 5m | 06 | 0.64 | 47547 | -100.0 | 0.58 | 1.00 |
| sm20_07_HYPEUSDT_1m | `2edcb60857227474` | HYPEUSDT 1m | 07 | 0.48 | 2624 | -100.0 | 0.49 | 0.93 |
| sm20_07_HYPEUSDT_5m | `d5c40dc86d533c75` | HYPEUSDT 5m | 07 | 0.59 | 6072 | -100.0 | 0.61 | 1.00 |
| sm20_07_SOLUSDT_1m | `f7b0e633b70514ea` | SOLUSDT 1m | 07 | 0.50 | 723 | -93.2 | 0.57 | 1.06 |
| sm20_07_SOLUSDT_5m | `968d78891a458190` | SOLUSDT 5m | 07 | 0.76 | 25121 | -100.0 | 0.69 | 1.01 |
| sm20_07_SUIUSDT_1m | `5347e1f5995ac08d` | SUIUSDT 1m | 07 | 0.54 | 2096 | -100.0 | 0.60 | 0.99 |
| sm20_07_SUIUSDT_5m | `2255211eef5de1fe` | SUIUSDT 5m | 07 | 0.65 | 14836 | -100.0 | 0.54 | 1.00 |
| sm20_08_HYPEUSDT_1m | `c77f0dc9280e241e` | HYPEUSDT 1m | 08 | 0.60 | 2530 | -100.0 | 0.62 | 0.99 |
| sm20_08_HYPEUSDT_5m | `d158ef6e8b2ba945` | HYPEUSDT 5m | 08 | 0.68 | 6225 | -100.0 | 0.67 | 1.01 |
| sm20_08_SOLUSDT_1m | `4f286f00f7e14a76` | SOLUSDT 1m | 08 | 0.49 | 660 | -93.6 | 0.54 | 0.97 |
| sm20_08_SOLUSDT_5m | `29cfe69f7ffd21e5` | SOLUSDT 5m | 08 | 0.87 | 24567 | -100.0 | 0.66 | 1.04 |
| sm20_08_SUIUSDT_1m | `df30c87dfa7c78c2` | SUIUSDT 1m | 08 | 0.60 | 1953 | -99.9 | 0.58 | 1.03 |
| sm20_08_SUIUSDT_5m | `6afb6dd1b3214767` | SUIUSDT 5m | 08 | 0.71 | 15068 | -100.0 | 0.58 | 1.00 |
| sm20_09_HYPEUSDT_1m | `e67360dbd4b27bee` | HYPEUSDT 1m | 09 | 0.50 | 6361 | -100.0 | 0.55 | 0.92 |
| sm20_09_HYPEUSDT_5m | `750eb8cd2a926e04` | HYPEUSDT 5m | 09 | 0.65 | 14882 | -100.0 | 0.72 | 0.98 |
| sm20_09_SOLUSDT_1m | `5181634e74960031` | SOLUSDT 1m | 09 | 0.52 | 1847 | -99.9 | 0.54 | 1.03 |
| sm20_09_SOLUSDT_5m | `7ecb0bf005feb9ab` | SOLUSDT 5m | 09 | 0.74 | 60333 | -100.0 | 0.62 | 1.00 |
| sm20_09_SUIUSDT_1m | `4c7c2b203622eb6a` | SUIUSDT 1m | 09 | 0.49 | 5089 | -100.0 | 0.60 | 1.06 |
| sm20_09_SUIUSDT_5m | `e67e9d2b83510ec2` | SUIUSDT 5m | 09 | 0.69 | 35948 | -100.0 | 0.67 | 1.00 |
| sm20_10_HYPEUSDT_1m | `a1ad596f37289fd0` | HYPEUSDT 1m | 10 | 0.56 | 1775 | -99.9 | 0.52 | 0.95 |
| sm20_10_HYPEUSDT_5m | `ac45544eae220188` | HYPEUSDT 5m | 10 | 0.65 | 3936 | -100.0 | 0.66 | 0.96 |
| sm20_10_SOLUSDT_1m | `18fa49a498a87f8a` | SOLUSDT 1m | 10 | 0.47 | 583 | -92.1 | 0.49 | 0.91 |
| sm20_10_SOLUSDT_5m | `97e641f8fdbcb52e` | SOLUSDT 5m | 10 | 0.79 | 16411 | -100.0 | 0.65 | 0.98 |
| sm20_10_SUIUSDT_1m | `d1b41f7f4873859b` | SUIUSDT 1m | 10 | 0.59 | 1520 | -99.7 | 0.46 | 0.99 |
| sm20_10_SUIUSDT_5m | `a6873286f870f436` | SUIUSDT 5m | 10 | 0.60 | 9666 | -100.0 | 0.59 | 1.00 |
| sm20_11_HYPEUSDT_1m | `19217b383a99d321` | HYPEUSDT 1m | 11 | 0.58 | 3150 | -100.0 | 0.48 | 0.97 |
| sm20_11_HYPEUSDT_5m | `eb87365f45e4c30d` | HYPEUSDT 5m | 11 | 0.68 | 7411 | -100.0 | 0.67 | 0.97 |
| sm20_11_SOLUSDT_1m | `b00a7ec97bd8bd56` | SOLUSDT 1m | 11 | 0.55 | 869 | -97.2 | 0.55 | 0.98 |
| sm20_11_SOLUSDT_5m | `73fc5ff31e6aff90` | SOLUSDT 5m | 11 | 0.81 | 29095 | -100.0 | 0.74 | 1.00 |
| sm20_11_SUIUSDT_1m | `76e76bfd6cd24149` | SUIUSDT 1m | 11 | 0.53 | 2493 | -100.0 | 0.56 | 0.94 |
| sm20_11_SUIUSDT_5m | `aa4c2619e015c059` | SUIUSDT 5m | 11 | 0.70 | 17393 | -100.0 | 0.64 | 1.00 |
| sm20_12_HYPEUSDT_1m | `9637183d5838200d` | HYPEUSDT 1m | 12 | 0.40 | 916 | -98.0 | 0.46 | 0.90 |
| sm20_12_HYPEUSDT_5m | `a50c0067b1aaeb9c` | HYPEUSDT 5m | 12 | 0.58 | 4547 | -100.0 | 0.55 | 0.97 |
| sm20_12_SOLUSDT_1m | `9d713c890c02f0e4` | SOLUSDT 1m | 12 | 0.32 | 264 | -77.0 | 0.33 | 0.70 |
| sm20_12_SOLUSDT_5m | `e2799ad681fea85e` | SOLUSDT 5m | 12 | 0.72 | 17892 | -100.0 | 0.64 | 1.02 |
| sm20_12_SUIUSDT_1m | `29296956eac883a1` | SUIUSDT 1m | 12 | 0.57 | 716 | -90.2 | 0.59 | 1.12 |
| sm20_12_SUIUSDT_5m | `aea417cdcaf922ac` | SUIUSDT 5m | 12 | 0.61 | 10809 | -100.0 | 0.57 | 1.03 |
| sm20_13_HYPEUSDT_1m | `04e5b7ecd459c372` | HYPEUSDT 1m | 13 | 0.58 | 1557 | -99.8 | 0.52 | 0.99 |
| sm20_13_HYPEUSDT_5m | `79f722d6fed9b9dd` | HYPEUSDT 5m | 13 | 0.69 | 3633 | -100.0 | 0.64 | 1.00 |
| sm20_13_SOLUSDT_1m | `aad2c1b4d7c5fd55` | SOLUSDT 1m | 13 | 0.43 | 431 | -87.9 | 0.61 | 0.86 |
| sm20_13_SOLUSDT_5m | `b0b7c5c938f20bfc` | SOLUSDT 5m | 13 | 0.85 | 13726 | -100.0 | 0.70 | 1.02 |
| sm20_13_SUIUSDT_1m | `d0854870992def38` | SUIUSDT 1m | 13 | 0.61 | 1229 | -98.5 | 0.63 | 1.06 |
| sm20_13_SUIUSDT_5m | `b271e86b99e19140` | SUIUSDT 5m | 13 | 0.64 | 8583 | -100.0 | 0.62 | 1.00 |
| sm20_14_HYPEUSDT_1m | `1ea6791016a1ec0a` | HYPEUSDT 1m | 14 | 0.54 | 3750 | -100.0 | 0.48 | 0.91 |
| sm20_14_HYPEUSDT_5m | `38fa004115081c5f` | HYPEUSDT 5m | 14 | 0.61 | 8685 | -100.0 | 0.68 | 0.99 |
| sm20_14_SOLUSDT_1m | `69080833857d5f6a` | SOLUSDT 1m | 14 | 0.51 | 988 | -97.5 | 0.71 | 1.05 |
| sm20_14_SOLUSDT_5m | `9fc6ee5df4640200` | SOLUSDT 5m | 14 | 0.85 | 34658 | -100.0 | 0.76 | 1.01 |
| sm20_14_SUIUSDT_1m | `8071ec0787ba34eb` | SUIUSDT 1m | 14 | 0.64 | 2924 | -100.0 | 0.64 | 1.03 |
| sm20_14_SUIUSDT_5m | `4e8d03212cae9cda` | SUIUSDT 5m | 14 | 0.69 | 20679 | -100.0 | 0.64 | 1.01 |
| sm20_15_HYPEUSDT_1m | `469d82c6028a8a9c` | HYPEUSDT 1m | 15 | 0.54 | 1311 | -99.7 | 0.48 | 0.92 |
| sm20_15_HYPEUSDT_5m | `fe7b9182e9593a45` | HYPEUSDT 5m | 15 | 0.61 | 3410 | -100.0 | 0.55 | 0.93 |
| sm20_15_SOLUSDT_1m | `d1fde226c575ba60` | SOLUSDT 1m | 15 | 0.59 | 286 | -65.1 | 0.59 | 1.08 |
| sm20_15_SOLUSDT_5m | `1cc6dfd6d252dccb` | SOLUSDT 5m | 15 | 0.87 | 13731 | -100.0 | 0.65 | 1.00 |
| sm20_15_SUIUSDT_1m | `0a606d54dd17a507` | SUIUSDT 1m | 15 | 0.51 | 1004 | -98.5 | 0.54 | 0.95 |
| sm20_15_SUIUSDT_5m | `46c65b53c68c64a9` | SUIUSDT 5m | 15 | 0.62 | 8146 | -100.0 | 0.56 | 1.00 |
| sm20_16_HYPEUSDT_1m | `aaaf02aaf16a91d9` | HYPEUSDT 1m | 16 | 0.50 | 3285 | -100.0 | 0.56 | 0.92 |
| sm20_16_HYPEUSDT_5m | `c104e37650ca4b2b` | HYPEUSDT 5m | 16 | 0.58 | 7303 | -100.0 | 0.69 | 0.91 |
| sm20_16_SOLUSDT_1m | `83456e721669aaa2` | SOLUSDT 1m | 16 | 0.53 | 899 | -97.6 | 0.55 | 0.97 |
| sm20_16_SOLUSDT_5m | `0e65bca180992c19` | SOLUSDT 5m | 16 | 0.94 | 27882 | -100.0 | 0.66 | 1.00 |
| sm20_16_SUIUSDT_1m | `f4a970de659ca03e` | SUIUSDT 1m | 16 | 0.58 | 2634 | -100.0 | 0.60 | 1.00 |
| sm20_16_SUIUSDT_5m | `e68e288c3f805e82` | SUIUSDT 5m | 16 | 0.66 | 16773 | -100.0 | 0.61 | 1.01 |
| sm20_17_HYPEUSDT_1m | `182501dd18c148ac` | HYPEUSDT 1m | 17 | 0.47 | 3009 | -100.0 | 0.55 | 0.87 |
| sm20_17_HYPEUSDT_5m | `e7832bc04e2643a5` | HYPEUSDT 5m | 17 | 0.66 | 6257 | -100.0 | 0.63 | 0.91 |
| sm20_17_SOLUSDT_1m | `22d9fc72682f610e` | SOLUSDT 1m | 17 | 0.50 | 898 | -97.8 | 0.50 | 0.95 |
| sm20_17_SOLUSDT_5m | `ad8098df712770f2` | SOLUSDT 5m | 17 | 0.86 | 24708 | -100.0 | 0.63 | 1.00 |
| sm20_17_SUIUSDT_1m | `49357cf670df4709` | SUIUSDT 1m | 17 | 0.54 | 2431 | -100.0 | 0.61 | 0.97 |
| sm20_17_SUIUSDT_5m | `9cb05794f6239a7a` | SUIUSDT 5m | 17 | 0.68 | 14369 | -100.0 | 0.69 | 1.00 |
| sm20_18_HYPEUSDT_1m | `6021d949744eb7cb` | HYPEUSDT 1m | 18 | 0.57 | 84 | -14.9 | 0.26 | 0.99 |
| sm20_18_HYPEUSDT_5m | `a46018634795a114` | HYPEUSDT 5m | 18 | 0.67 | 805 | -68.5 | 0.61 | 1.02 |
| sm20_18_SOLUSDT_1m | `badee3dad8714a92` | SOLUSDT 1m | 18 | 0.43 | 16 | -4.5 | inf | 0.73 |
| sm20_18_SOLUSDT_5m | `2c7966b39b4df0b7` | SOLUSDT 5m | 18 | 0.70 | 3471 | -99.1 | 0.64 | 1.02 |
| sm20_18_SUIUSDT_1m | `42e5e9025bd8044b` | SUIUSDT 1m | 18 | 0.51 | 87 | -19.3 | 0.38 | 0.82 |
| sm20_18_SUIUSDT_5m | `56eb4b3e4664d78a` | SUIUSDT 5m | 18 | 0.65 | 2168 | -96.7 | 0.68 | 0.98 |
| sm20_19_HYPEUSDT_1m | `8c845106f1e7d890` | HYPEUSDT 1m | 19 | 0.57 | 591 | -90.1 | 0.35 | 0.96 |
| sm20_19_HYPEUSDT_5m | `d8263f9ce67bd6f7` | HYPEUSDT 5m | 19 | 0.66 | 1160 | -96.1 | 0.65 | 0.93 |
| sm20_19_SOLUSDT_1m | `01092070e97c61b2` | SOLUSDT 1m | 19 | 0.57 | 191 | -49.4 | 0.54 | 1.05 |
| sm20_19_SOLUSDT_5m | `58f80a4e5fc13634` | SOLUSDT 5m | 19 | 0.83 | 5013 | -100.0 | 0.62 | 0.99 |
| sm20_19_SUIUSDT_1m | `ce7d3861dfefc4e5` | SUIUSDT 1m | 19 | 0.54 | 514 | -88.0 | 0.51 | 0.92 |
| sm20_19_SUIUSDT_5m | `c3478b8711fc24a5` | SUIUSDT 5m | 19 | 0.69 | 2853 | -99.9 | 0.57 | 0.99 |
| sm20_20_HYPEUSDT_1m | `f4b9fc32c74d797d` | HYPEUSDT 1m | 20 | 0.52 | 2949 | -100.0 | 0.54 | 0.95 |
| sm20_20_HYPEUSDT_5m | `dd8e9f59f2275373` | HYPEUSDT 5m | 20 | 0.56 | 6407 | -100.0 | 0.66 | 0.92 |
| sm20_20_SOLUSDT_1m | `b014f299156b3cea` | SOLUSDT 1m | 20 | 0.60 | 865 | -97.4 | 0.43 | 0.97 |
| sm20_20_SOLUSDT_5m | `ce2951da28db3b2f` | SOLUSDT 5m | 20 | 0.91 | 23982 | -100.0 | 0.66 | 1.00 |
| sm20_20_SUIUSDT_1m | `a1ae0e2df9e9ed59` | SUIUSDT 1m | 20 | 0.56 | 2399 | -100.0 | 0.67 | 1.04 |
| sm20_20_SUIUSDT_5m | `f3bc57746775519e` | SUIUSDT 5m | 20 | 0.67 | 14776 | -100.0 | 0.68 | 1.00 |

## Mechanism (why it dies)

- **No gross edge above the gate.** With fees and slippage switched off (funding
  still charged), the zero-cost control reaches a profit factor above one on
  fifty of the one hundred twenty cells, but NEVER above one point two. The
  highest zero-cost profit factor in the family is 1.12 on
  SUIUSDT 1m id12 `29296956eac883a1`.
  The signal itself is marginal before costs; there is nothing for a better
  fill model to rescue.
- **Cost ruin at the house regime.** Net of eleven bps round trip the highest
  profit factor in the family is 0.94 on SOLUSDT
  5m id16 `0e65bca180992c19` — still below one.
  The busiest cell, SOLUSDT 5m id16
  `0e65bca180992c19`, pays 38435.59 USDT in fees on the initial
  equity over 27882 closed trades. Turnover, not a misplaced constant,
  is the loss pattern.
- **The cost gate removes most signals on the fine tape.** On
  SOLUSDT 1m id06 `56db4c6bb9b5c44b`
  the gate skips 27974 of 30459 raw signals
  (target distance under three-x the round trip). That removal is itself the
  finding: at one minute the typical target does not clear the cost wall.
- **Least-bad cell still fails.** SOLUSDT 1m
  id18 `badee3dad8714a92` nets -4.5 percent
  at profit factor 0.43 on 16 trades — under the
  thirty-trade floor, and its zero-cost profit factor is 0.73 (it loses
  before costs too).
- **Degenerate out-of-sample, NOT evidence.** SOLUSDT 1m
  id18 `badee3dad8714a92` prints an infinite out-of-sample profit
  factor because its out-of-sample subset contains no losing trades on a
  16-trade sample. It fails the trade floor and every other gate. An
  infinite profit factor on a handful of trades is a small-sample artifact, not a pass.

## Multiple testing

One hundred twenty cells times eight gates on overlapping data. Zero passes is
far below what noise alone would produce at this gate; there is no survivor to
correct, and no neighborhood peak to chase. Per REGLA 1 each id is judged only
on its own artifacts; no 'best of family' claim is made.

## Passive context

Passive buy-and-hold over the traded windows was positive on five of the six
symbol-by-timeframe windows (the exception is SUI five-minute). Every strategy
cell loses in ABSOLUTE terms, so the verdict does not depend on the passive
comparison — these books wipe out while passive mostly rises.

## Artifacts and verification

One hundred twenty artifacts in `results/runs/`, each sha-bound to the engine,
the kline CSV and the funding JSON, cut at the creation day. Bit-for-bit
verification: `results/_scalpma20_verify.txt`. Machine-readable matrix:
`results/scalpma20_matrix.json`. Pre-registered plan: `results/bt_plans/scalpma20.json`.

Do not re-run this family expecting a different verdict: the failure is cost and
a sub-gate gross edge, not a parameter. The revisit trigger is a signal whose
ZERO-COST profit factor clears one point two on its own artifact — none does.
