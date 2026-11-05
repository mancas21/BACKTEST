#!/usr/bin/env bash
# deploy_xrp_paper_bot.sh — install the "XRP paper bot" on the VPS.
#
# It is a SEPARATE bot from the others on the box: its own directory, its own
# service name, its own log, its own state files, and its own cron line. Nothing
# it does can touch ~/paper, ~/grid-paper, ~/cqb or ~/freqtrade.
#
# Idempotent: re-running updates the code and leaves the state files alone.
#
# Usage:  bash deploy_xrp_paper_bot.sh [--init]
#           --init  also freeze the Day-0 baseline after the first data pull
set -euo pipefail

BOT_DIR=/home/ubuntu/xrp-paper-bot
CRON_LINE='*/5 * * * * /home/ubuntu/xrp-paper-bot/run.sh'
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DO_INIT=0
[ "${1:-}" = "--init" ] && DO_INIT=1

echo "== XRP paper bot deploy =="
echo "   source : $SRC_DIR"
echo "   target : $BOT_DIR"

mkdir -p "$BOT_DIR/data/binance_klines_15m" "$BOT_DIR/data/binance_funding"

# the engine and the runner. Nothing else is needed: the engine is self-contained
# (no cvrmd_port, no grid_audit) so it cannot break if the repo moves on.
for f in xrp_neutral_engine.py xrp_paper_bot.py; do
  if [ ! -f "$SRC_DIR/$f" ]; then
    echo "ERROR: missing $SRC_DIR/$f" >&2
    exit 1
  fi
  cp "$SRC_DIR/$f" "$BOT_DIR/$f"
  echo "   installed $f"
done

# the audit travels with it, so the deployed copy can be re-verified in place
for f in xrp_neutral_audit.py; do
  [ -f "$SRC_DIR/$f" ] && cp "$SRC_DIR/$f" "$BOT_DIR/$f" && echo "   installed $f"
done

cat > "$BOT_DIR/run.sh" <<'EOF'
#!/bin/bash
# XRP paper bot — one cycle per invocation. flock keeps a slow cycle from
# overlapping the next one, exactly like the other bots on this box.
cd /home/ubuntu/xrp-paper-bot || exit 1
exec 9>/tmp/xrp-paper-bot.lock
if ! flock -n 9; then echo "ya corriendo, salgo"; exit 0; fi
/usr/bin/python3 xrp_paper_bot.py --once >> /home/ubuntu/xrp-paper-bot/xrp_paper_bot.log 2>&1
rc=$?
echo "--- cycle $(date -u +%FT%TZ) rc=$rc ---" >> /home/ubuntu/xrp-paper-bot/xrp_paper_bot.log
exit $rc
EOF
chmod +x "$BOT_DIR/run.sh"
echo "   installed run.sh"

# cron: add our line exactly once, and never touch the other bots' lines
if crontab -l 2>/dev/null | grep -qF "$CRON_LINE"; then
  echo "   cron: line already present, left alone"
else
  ( crontab -l 2>/dev/null; echo "$CRON_LINE" ) | crontab -
  echo "   cron: added -> $CRON_LINE"
fi

# a watchdog: if the bot has not written a status file in 30 minutes, say so
cat > "$BOT_DIR/watchdog.sh" <<'EOF'
#!/bin/bash
# XRP paper bot watchdog. The failure that matters is SILENCE: a cron that dies
# leaves a status file that looks fine but is hours old. This is the same class
# of bug that let the local grid trackers go 21 days stale unnoticed.
S=/home/ubuntu/xrp-paper-bot/xrp_paper_bot_status.json
if [ ! -f "$S" ]; then echo "$(date -u +%FT%TZ) NO STATUS FILE"; exit 1; fi
AGE=$(( $(date +%s) - $(stat -c %Y "$S") ))
if [ "$AGE" -gt 1800 ]; then
  echo "$(date -u +%FT%TZ) STATUS STALE: ${AGE}s old"
  exit 1
fi
echo "$(date -u +%FT%TZ) ok (${AGE}s old)"
EOF
chmod +x "$BOT_DIR/watchdog.sh"
WATCH_LINE='17 * * * * /home/ubuntu/xrp-paper-bot/watchdog.sh >> /home/ubuntu/xrp-paper-bot/xrp_paper_bot.log 2>&1'
if crontab -l 2>/dev/null | grep -qF "$WATCH_LINE"; then
  echo "   watchdog: line already present, left alone"
else
  ( crontab -l 2>/dev/null; echo "$WATCH_LINE" ) | crontab -
  echo "   watchdog: added -> $WATCH_LINE"
fi

echo "== first cycle (pulls history; can take a few minutes) =="
sudo -u ubuntu env HOME=/home/ubuntu bash -c "cd $BOT_DIR && ./run.sh" || true
if [ -f "$BOT_DIR/xrp_paper_bot_status.json" ]; then
  echo "   status written:"
  python3 -c "import json;d=json.load(open('$BOT_DIR/xrp_paper_bot_status.json'));print('     ',d['updated_utc'],'equity',d['equity'],'bars',d['bars'],'pf',d['pf_all_closed'],'n',d['n_closed'])" 2>/dev/null || true
else
  echo "   WARNING: no status file yet (the history pull may still be running)"
fi

if [ "$DO_INIT" = "1" ]; then
  echo "== freezing the Day-0 baseline =="
  sudo -u ubuntu env HOME=/home/ubuntu bash -c "cd $BOT_DIR && /usr/bin/python3 xrp_paper_bot.py --init"
fi

echo "== done =="
echo "   bot dir : $BOT_DIR"
echo "   status  : $BOT_DIR/xrp_paper_bot_status.json"
echo "   log     : $BOT_DIR/xrp_paper_bot.log"
echo "   the other bots on this box are untouched: ~/paper ~/grid-paper ~/cqb ~/freqtrade"
