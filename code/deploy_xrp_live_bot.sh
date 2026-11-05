#!/usr/bin/env bash
# deploy_xrp_live_bot.sh — install the LIVE/TESTNET XRP neutral bot on the VPS.
#
# SEPARATE from every other bot on the box: /home/ubuntu/xrp-live-bot, its own
# cron line (offset +1 minute from the paper bot's */5), its own state files,
# its own data copy, its own .env. It cannot touch ~/xrp-paper-bot, ~/paper,
# ~/grid-paper, ~/cqb or ~/freqtrade.
#
# The install NEVER arms real-money trading. The path is:
#   1. put TESTNET keys in the .env below
#   2. bash deploy_xrp_live_bot.sh            (installs + runs --init testnet)
#   3. let the testnet cycles run; watch xrp_live_bot_recon.jsonl
#   4. only when the testnet stage has passed:
#        - put LIVE keys (futures ON, withdrawals OFF, IP-whitelisted) in .env
#        - python3 xrp_live_bot.py --arm-live --net live   (typed confirmation)
#
# Idempotent: re-running updates the code and leaves state files alone.
#
# Usage:  bash deploy_xrp_live_bot.sh [--net testnet|live]
set -euo pipefail

BOT_DIR=/home/ubuntu/xrp-live-bot
NET=testnet
[ "${1:-}" = "--net" ] && { NET="${2:-testnet}"; shift 2 || true; }
[ "${1:-}" = "--net" ] && NET="${2:-testnet}"

CRON_LINE='1-56/5 * * * * /home/ubuntu/xrp-live-bot/run.sh'
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== XRP live bot deploy (net=$NET) =="
echo "   source : $SRC_DIR"
echo "   target : $BOT_DIR"

mkdir -p "$BOT_DIR/data/binance_klines_15m" "$BOT_DIR/data/binance_funding"

# the engine (byte-locked, asserted by the bot itself), the paper bot as the
# data-pipeline library, the live executor, and the audit for in-place checks
for f in xrp_neutral_engine.py xrp_paper_bot.py xrp_live_bot.py xrp_neutral_audit.py; do
  if [ ! -f "$SRC_DIR/$f" ]; then
    echo "ERROR: missing $SRC_DIR/$f" >&2
    exit 1
  fi
  cp "$SRC_DIR/$f" "$BOT_DIR/$f"
  echo "   installed $f"
done

# ── keys: root-only .env, never committed, never logged ─────────────────────
ENV_FILE="$BOT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<'EOF'
# Binance API keys. Fill in the TESTNET pair first (testnet.binancefuture.com).
# The LIVE pair must have: futures enabled, WITHDRAWALS DISABLED, IP whitelist
# = this VPS. Copy the live pair in ONLY when the testnet stage has passed.
BINANCE_TESTNET_KEY=
BINANCE_TESTNET_SECRET=
BINANCE_LIVE_KEY=
BINANCE_LIVE_SECRET=
EOF
  chmod 600 "$ENV_FILE"
  echo "   created $ENV_FILE (chmod 600) - FILL IN THE TESTNET KEYS"
else
  chmod 600 "$ENV_FILE"
  echo "   .env present (chmod 600), left alone"
fi

cat > "$BOT_DIR/run.sh" <<EOF
#!/bin/bash
# XRP live bot — one cycle per invocation; flock keeps cycles from overlapping.
cd $BOT_DIR || exit 1
exec 9>/tmp/xrp-live-bot.lock
if ! flock -n 9; then echo "ya corriendo, salgo"; exit 0; fi
set -a; source $BOT_DIR/.env; set +a
export XRP_BOT_HOME=$BOT_DIR
/usr/bin/python3 $BOT_DIR/xrp_live_bot.py --once --net $NET >> $BOT_DIR/xrp_live_bot.log 2>&1
rc=\$?
echo "--- cycle \$(date -u +%FT%TZ) rc=\$rc ---" >> $BOT_DIR/xrp_live_bot.log
exit \$rc
EOF
chmod +x "$BOT_DIR/run.sh"
echo "   installed run.sh (net=$NET)"

# cron: our line only, offset +1 minute from the paper bot's */5
if crontab -l 2>/dev/null | grep -qF "$CRON_LINE"; then
  echo "   cron: line already present, left alone"
else
  ( crontab -l 2>/dev/null; echo "$CRON_LINE" ) | crontab -
  echo "   cron: added -> $CRON_LINE"
fi

# watchdog: silence is the failure that matters
cat > "$BOT_DIR/watchdog.sh" <<EOF
#!/bin/bash
S=$BOT_DIR/xrp_live_bot_status.json
if [ ! -f "\$S" ]; then echo "\$(date -u +%FT%TZ) NO STATUS FILE"; exit 1; fi
AGE=\$(( \$(date +%s) - \$(stat -c %Y "\$S") ))
if [ "\$AGE" -gt 1800 ]; then
  echo "\$(date -u +%FT%TZ) STATUS STALE: \${AGE}s old"
  exit 1
fi
# and the recon file must exist once trading starts
R=$BOT_DIR/xrp_live_bot_recon.jsonl
if [ -f "$BOT_DIR/.trading_started" ] && [ ! -f "\$R" ]; then
  echo "\$(date -u +%FT%TZ) TRADING BUT NO RECON FILE"; exit 1
fi
echo "\$(date -u +%FT%TZ) ok (\${AGE}s old)"
EOF
chmod +x "$BOT_DIR/watchdog.sh"
WATCH_LINE='17 * * * * /home/ubuntu/xrp-live-bot/watchdog.sh >> /home/ubuntu/xrp-live-bot/xrp_live_bot.log 2>&1'
if crontab -l 2>/dev/null | grep -qF "$WATCH_LINE"; then
  echo "   watchdog: line already present, left alone"
else
  ( crontab -l 2>/dev/null; echo "$WATCH_LINE" ) | crontab -
  echo "   watchdog: added -> $WATCH_LINE"
fi

echo "== first cycle (pulls history; can take a few minutes) =="
if grep -q "^BINANCE_TESTNET_KEY=..*" "$ENV_FILE" || \
   grep -q "^BINANCE_LIVE_KEY=..*" "$ENV_FILE"; then
  sudo -u ubuntu env HOME=/home/ubuntu bash -c \
    "cd $BOT_DIR && set -a && source .env && set +a && export XRP_BOT_HOME=$BOT_DIR && /usr/bin/python3 xrp_live_bot.py --init --net $NET" || true
  sudo -u ubuntu env HOME=/home/ubuntu bash -c \
    "cd $BOT_DIR && set -a && source .env && set +a && export XRP_BOT_HOME=$BOT_DIR && ./run.sh" || true
  if [ -f "$BOT_DIR/xrp_live_bot_status.json" ]; then
    echo "   status written:"
    python3 -c "import json;d=json.load(open('$BOT_DIR/xrp_live_bot_status.json'));print('     ',d['updated_utc'],'net',d['net'],'state',d.get('engine_state'),'wallet',d.get('wallet_usdt'))" 2>/dev/null || true
  else
    echo "   WARNING: no status file yet (check xrp_live_bot.log)"
  fi
else
  echo "   SKIPPED first cycle: no keys in .env yet"
fi

echo "== done =="
echo "   bot dir   : $BOT_DIR"
echo "   status    : $BOT_DIR/xrp_live_bot_status.json"
echo "   recon     : $BOT_DIR/xrp_live_bot_recon.jsonl  (the honesty check)"
echo "   log       : $BOT_DIR/xrp_live_bot.log"
echo
echo "   STAGE GATE: real money requires, in this order:"
echo "     1. the paper forward record clears its pre-registered review"
echo "     2. testnet cycles run clean (recon match, no recurring errors)"
echo "     3. LIVE keys into .env (withdrawals OFF, IP whitelist ON)"
echo "     4. python3 xrp_live_bot.py --arm-live --net live  (typed confirmation)"
echo "   The install itself never arms live."
