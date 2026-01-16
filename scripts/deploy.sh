#!/bin/bash
# Deploy script for Twitch Bot Handler
# Run on VPS: ./scripts/deploy.sh

set -e

INSTALL_DIR="/opt/twitchbot"
REPO_URL="https://github.com/omen4impact/twitch-bot.git"

echo "🔄 Deploying Twitch Bot Handler..."

cd "$INSTALL_DIR"

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt --quiet

# Restart service
sudo systemctl restart twitch-handler

# Check status
sleep 2
if systemctl is-active --quiet twitch-handler; then
    echo "✅ Deployment complete! Service is running."
else
    echo "❌ Service failed to start. Check logs:"
    echo "   sudo journalctl -u twitch-handler -n 50"
    exit 1
fi
