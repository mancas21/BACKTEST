# MP-18 v2 Paper Trading — VPS Deployment Guide

## Prerequisites
- VPS with Ubuntu 22.04+ (or any Linux)
- Python 3.10+ (3.12 recommended)
- Internet access to Binance API

## Step 1: Install Python and dependencies

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y python3 python3-pip python3-venv

# Create virtual environment
python3 -m venv /opt/mp18/venv
source /opt/mp18/venv/bin/activate

# Install dependencies
pip install pandas numpy
```

## Step 2: Deploy code

```bash
# Create directory structure
mkdir -p /opt/mp18/backtest-system/code
mkdir -p /opt/mp18/backtest-system/data

# Copy mp18_v2_paper.py to /opt/mp18/backtest-system/code/
# (upload via scp, rsync, or copy-paste)
```

## Step 3: Initialize (first run)

```bash
cd /opt/mp18/backtest-system
source /opt/mp18/venv/bin/activate
python code/mp18_v2_paper.py --init
```

This will:
- Download ~6 years of 1h data for 11 pairs (~682k bars, takes 5-10 min)
- Compute baseline weights
- Freeze baseline equity
- Create status and ledger files

## Step 4: Set up cron

```bash
# Edit crontab
crontab -e

# Add this line (runs every hour at minute 5):
5 * * * * cd /opt/mp18/backtest-system && /opt/mp18/venv/bin/python code/mp18_v2_paper.py >> logs/paper.log 2>&1

# Create logs directory
mkdir -p /opt/mp18/backtest-system/logs
```

## Step 5: Monitor

```bash
# Check status
cat /opt/mp18/backtest-system/mp18_v2_paper_status.json

# Check ledger
cat /opt/mp18/backtest-system/mp18_v2_paper_ledger.csv

# Check logs
tail -20 /opt/mp18/backtest-system/logs/paper.log
```

## Files created

| File | Description |
|------|-------------|
| `code/mp18_v2_paper.py` | Paper trading tracker |
| `mp18_v2_paper_baseline.json` | Frozen baseline |
| `mp18_v2_paper_status.json` | Current status |
| `mp18_v2_paper_ledger.csv` | Cycle history |
| `data/binance_klines_1h/*.csv` | Price data |
| `logs/paper.log` | Cron output |

## Troubleshooting

- **No data / empty panel**: Check internet connectivity to Binance API
- **Permission errors**: Ensure the user running cron has write access to the directory
- **Cron not running**: Check `crontab -l` and `/var/log/syslog` for cron errors
- **Python not found**: Use full path to venv python in crontab

## To sync results back to local machine

```bash
# From local machine:
scp user@vps:/opt/mp18/backtest-system/mp18_v2_paper_status.json ./
scp user@vps:/opt/mp18/backtest-system/mp18_v2_paper_ledger.csv ./
```