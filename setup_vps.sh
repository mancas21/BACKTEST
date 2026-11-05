#!/bin/bash
# setup_vps.sh — deploy MP-18 v2 paper trading to VPS
# Run as: bash setup_vps.sh

set -e

INSTALL_DIR="/opt/mp18"
VENV="$INSTALL_DIR/venv"
PROJECT="$INSTALL_DIR/backtest-system"

echo "=== MP-18 v2 Paper Trading — VPS Setup ==="

# 1. Install Python
if ! command -v python3 &>/dev/null; then
    echo "Installing Python..."
    sudo apt update && sudo apt install -y python3 python3-pip python3-venv
fi

# 2. Create venv
if [ ! -d "$VENV" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"

# 3. Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install pandas numpy

# 4. Create directory structure
mkdir -p "$PROJECT/code" "$PROJECT/data" "$PROJECT/logs"

# 5. Copy code (assumes mp18_v2_paper.py is in current directory)
if [ -f "mp18_v2_paper.py" ]; then
    cp mp18_v2_paper.py "$PROJECT/code/"
    echo "Copied mp18_v2_paper.py"
else
    echo "WARNING: mp18_v2_paper.py not found in current directory"
    echo "Please copy it manually to $PROJECT/code/"
fi

# 6. Initialize
echo "Initializing (downloading data — this may take 5-10 minutes)..."
cd "$PROJECT"
python code/mp18_v2_paper.py --init

# 7. Set up cron
echo "Setting up cron..."
(crontab -l 2>/dev/null || true; echo "5 * * * * cd $PROJECT && $VENV/bin/python code/mp18_v2_paper.py >> logs/paper.log 2>&1") | crontab -

echo ""
echo "=== Setup complete ==="
echo "Status: cat $PROJECT/mp18_v2_paper_status.json"
echo "Ledger: cat $PROJECT/mp18_v2_paper_ledger.csv"
echo "Logs:   tail -f $PROJECT/logs/paper.log"
echo "Cron:   crontab -l"