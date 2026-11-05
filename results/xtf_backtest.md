# Cross-timeframe backtest - 1m / 15m / 1h (+ 5m reference) - seven symbols

Every number below is read from vrun artifacts in `results/runs/`; each `verify`s
bit-for-bit. None was typed by hand. Data: Binance USD-M futures WITH kline field 9
(`taker_buy_base`), which is what makes S05 taker-flow and S06 CVD divergence testable
at all. Fetched by `code/fetch_taker_tf.py`.

## cbot 10-strategy suite - passes out of ten per cell

| tf | hold | BTCUSDT | ETHUSDT | SOLUSDT | XRPUSDT | SUIUSDT | JUPUSDT | HYPEUSDT |
|---|---|---|---|---|---|---|---|---|
| 1m | 3m || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 |
| 1m | 15m || 2/10 || 1/10 || 1/10 || 0/10 || 0/10 || 0/10 || 1/10 |
| 15m | 45m || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 |
| 15m | 15m || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 |
| 1h | 180m || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 |
| 1h | 60m || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 |
| 5m | 15m || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 || 0/10 |
| 5m | 15m || not run || not run || not run || not run || not run || 0/10 || 0/10 |

**5 passes out of 510 strategy-runs.**

Two config notes:
- At 5m the two hold modes coincide (a three-bar hold and a fifteen-minute hold are the
  same thing), so that row was run twice under different ids with identical metrics.
- HYPEUSDT has a shorter history than the others (724524 one-minute
  bars against 1051200 for JUP), because its perpetual listed late. It
  is reported in its own column and not pooled with BTC.

## 1m: the only timeframe that ever produced a pass - and the split that killed it

AGENTS.md requires green in at least two of three periods. The same 1m fifteen-minute-hold
config, re-run on three consecutive windows:

| sym | P1 | P2 | P3 |
|---|---|---|---
| BTCUSDT || `f4d8aeb8daed1041` 0/10 || `6be62afb3c88e373` 1/10 || `a0cf558a3d87dee9` 0/10 ||
| ETHUSDT || `0b9ecedc3af03e61` 0/10 || `ec73451283910de6` 2/10 || `40450a5a486088c0` 0/10 ||
| SOLUSDT || `72eed2a3e0d8ba11` 0/10 || `a1410ecf334b4643` 0/10 || `a1efe4befd8c0326` 1/10 ||
| HYPEUSDT || `e5e863e4d53a0188` 0/10 || `5ddf014281dcfcb4` 0/10 || `d736d11929becff6` 0/10 ||

**4 passing periods out of twelve.** BTC and ETH are green in one period each,
SOL in one, HYPE in none. Nothing reaches two of three. On BTC and SOL the strategy that
passes in a period is not the one that passed the aggregate.

## The other engines at the same timeframes

Their rules are bar-indexed, so evaluating them on a different bar size rescales what the
rules mean (CVRMD's RSI14 is fourteen hours at 1h and fourteen minutes at 1m). A positive
cell here is evidence about timeframe-dependence, NOT a validated strategy at that
timeframe.

| engine | tf | artifacts | positive | PF range | return range |
|---|---|---|---|---|---|
| cvrmd | 15m | 6 | 0 | 0.601-1.004 | -65.6% to -0.2% |
| | | | | | `826345c6710870f5` `ce36ef3b97778d5d` `c899ab864bda4c18` `23f91cdfb2b82679` `49f69acae3c5a42f` `2438df16b5088ee8` |
| cvrmd | 1h | 25 | 12 | 0.652-1.788 | -14.5% to +16.7% |
| | | | | | `431127ec50f96e16` `f8e856dacb5fbbd2` `c86439c3c5534fac` `d49c9b6b993e9a9a` `1e6d5ad221e0b6eb` `940831bb3fc8ed8b` `991949ff7ed940fe` `ddc3af0a45e60670` `3f8c5dd54278825c` `74e51a4ad5c59bb3` `3daeeeb4b2d2f316` `5e9599a41dc09d30` `6727aeb50edb9bea` `7d3c255a91f0652b` `fff94bf483860d15` `21aa88f786968664` `2a295b1756338181` `1929d0f6c93a6bab` `64eb32e3269b0d42` `aa84ff4de9e1dbd9` `6c0d6968b61b0871` `705d73e88fc192fd` `f81a0f5ddd95fdc2` `5782b8db04b4bdcb` `d0c5856746eb4e77` |
| botstrat | 15m | 6 | 5 | 0.917-1.424 | -3.0% to +54.3% |
| | | | | | `962abff991a2470d` `118526bf08e1de28` `e3dcfdb0a898c6ea` `fbc666a39ec615e6` `ea69e381a1138c25` `4c6b3e46b4ab1533` |
| botstrat | 1h | 14 | 9 | 0.541-3.079 | -21.1% to +51.4% |
| | | | | | `3395d8614f6f060d` `80ed06ac9997dd63` `79cb2fba8cfc251c` `03ccd1e99e274c87` `75c101d35f97fce0` `aa84bbc564f36008` `c71737e334322c99` `00f61536cddb22a3` `9118223dee1efba7` `9e6e85ff95700ef5` `40c1a07e484e0205` `f2aa1050b118e54f` `1bf2aff96c74fa93` `f063bb055aa6daaa` |
| ffs | 15m | 6 | 0 | 0.767-1.005 | -90.4% to -11.5% |
| | | | | | `8401f883c2690b1b` `d0c8668b1a74f804` `7a0dcdd7a146e941` `dadfd123db4f8448` `c70a28983cdcdd4a` `1855e3a9ca59da0b` |
| ffs | 1h | 13 | 0 | 0.551-0.849 | -61.6% to -11.2% |
| | | | | | `f98aed64127f130e` `cb7d8733cfbd8e46` `b155825805413aa5` `26f3bbd0c2251cfc` `a9f6a20c8bdf14d6` `dbd9b70e75cd84da` `c75ddd77dcff297e` `413474ab8e691aee` `3001e53cce8648a4` `e85aa74274cd3f1e` `6916073f822ec7df` `59260cd720354f39` `92a5bd883fec3e1f` |
**sax cannot be run at all.** Its engine source
(`Downloads/sax_engine-claude.py`) no longer exists on disk, so every pre-existing SAX
artifact now fails `verify` with FileNotFoundError. SAX was already killed, so no
conclusion changes, but the repository can no longer reproduce its own SAX evidence.

## VERDICT

**KILLED at every timeframe on every symbol tested.** The suite carries no directional
information from one minute upward. The only configurations that ever passed did so on an
aggregate window and failed the period split - the signature of a selected sample, not an
edge. A permutation control shuffles predictions WITHIN a sample and therefore cannot
detect this; the period split is a separate, mandatory gate.

## Reproduction

```
python code\fetch_taker_tf.py --tf 1m --sym HYPEUSDT
python code\vrun.py run    --strategy cbot --tf 1m --symbol HYPEUSDT --set hold_mode=minutes
python code\_xtf_periods.py HYPEUSDT 1m minutes 3
python code\vrun.py verify b6c21d27ee6700ae
```

## run_id index for the pass matrix

| tf | hold | sym | run_id |
|---|---|---|---|
| 1m | 3m | BTCUSDT | `ccb5e182158b3405` |
| 1m | 3m | ETHUSDT | `ba53d34ac48a9dbd` |
| 1m | 3m | SOLUSDT | `9921801375866faf` |
| 1m | 3m | XRPUSDT | `77bbb47dddb4a4f2` |
| 1m | 3m | SUIUSDT | `d0e024bcd6ebd85d` |
| 1m | 3m | JUPUSDT | `b8dda4894fd9adfc` |
| 1m | 3m | HYPEUSDT | `408e69ff4b1709e0` |
| 1m | 15m | BTCUSDT | `d2048ac32b01126b` |
| 1m | 15m | ETHUSDT | `b113de7b4f745354` |
| 1m | 15m | SOLUSDT | `079aadeaa00057ac` |
| 1m | 15m | XRPUSDT | `1a8d1d66636f0e19` |
| 1m | 15m | SUIUSDT | `94fe9f410b93735a` |
| 1m | 15m | JUPUSDT | `7cfb9f064dbcabb0` |
| 1m | 15m | HYPEUSDT | `b6c21d27ee6700ae` |
| 15m | 45m | BTCUSDT | `e74b34b0d081dede` |
| 15m | 45m | ETHUSDT | `a5f17be85d46a8a3` |
| 15m | 45m | SOLUSDT | `83d7b22a9d9c58b1` |
| 15m | 45m | XRPUSDT | `ebcd0395863b5ff0` |
| 15m | 45m | SUIUSDT | `1cfd358b260bb7d0` |
| 15m | 45m | JUPUSDT | `c2d2ad3882a5af56` |
| 15m | 45m | HYPEUSDT | `f64e6df6f8e1101c` |
| 15m | 15m | BTCUSDT | `412dc10538e78196` |
| 15m | 15m | ETHUSDT | `0576c8625c950972` |
| 15m | 15m | SOLUSDT | `6a80b6e21c5d4859` |
| 15m | 15m | XRPUSDT | `b2ab544859b6f055` |
| 15m | 15m | SUIUSDT | `fc60626e517f35b6` |
| 15m | 15m | JUPUSDT | `d14561960c46c4e1` |
| 15m | 15m | HYPEUSDT | `ac4f701b43140e5a` |
| 1h | 180m | BTCUSDT | `ab5a006b573b4f42` |
| 1h | 180m | ETHUSDT | `5e26207490a7b9f7` |
| 1h | 180m | SOLUSDT | `dc8b502797bcd913` |
| 1h | 180m | XRPUSDT | `e498fee31aa58d99` |
| 1h | 180m | SUIUSDT | `5f8480ffd8d6b675` |
| 1h | 180m | JUPUSDT | `fd7e6836f61f8b5b` |
| 1h | 180m | HYPEUSDT | `805b8316f7b3c1ed` |
| 1h | 60m | BTCUSDT | `484de3169325af57` |
| 1h | 60m | ETHUSDT | `774a1401dda1c2e6` |
| 1h | 60m | SOLUSDT | `541ddf229a4f65bd` |
| 1h | 60m | XRPUSDT | `0fdf2779c8d0c689` |
| 1h | 60m | SUIUSDT | `f18b44bb36f456b1` |
| 1h | 60m | JUPUSDT | `d25a1fb936712945` |
| 1h | 60m | HYPEUSDT | `a376a4378462ab1d` |
| 5m | 15m | BTCUSDT | `8a70837fb8e5deb2` |
| 5m | 15m | ETHUSDT | `ca064d3283a086ee` |
| 5m | 15m | SOLUSDT | `c5b4a8d8099671e0` |
| 5m | 15m | XRPUSDT | `995a7fe94daf2126` |
| 5m | 15m | SUIUSDT | `cbacef4f775d6551` |
| 5m | 15m | JUPUSDT | `a37b0692219142f6` |
| 5m | 15m | HYPEUSDT | `9705f4225fed35b6` |
| 5m | 15m | JUPUSDT | `7dfdba2f3a528e8f` |
| 5m | 15m | HYPEUSDT | `6f318809811fbc68` |
