#!/bin/bash
# ─── EC2 Deploy Script ────────────────────────────────────────────────────────
# Run this ON the EC2 instance after SSH-ing in:
#   ssh -i device.pem ubuntu@<EC2_IP>
#   bash deploy.sh

set -e

APP_DIR="/home/ubuntu/resume-hub"
REPO="https://github.com/ad4rush/Knowledge-Graph.git"
BRANCH="master"

echo "=== Resume Hub — EC2 Deploy ==="

# Install Docker if missing
if ! command -v docker &>/dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker ubuntu
    newgrp docker
fi

# Install Docker Compose plugin if missing
if ! docker compose version &>/dev/null; then
    sudo apt-get install -y docker-compose-plugin
fi

# Clone or update repo
if [ -d "$APP_DIR/.git" ]; then
    echo "Pulling latest code..."
    cd $APP_DIR
    git fetch origin
    git reset --hard origin/$BRANCH
else
    echo "Cloning repo..."
    git clone --branch $BRANCH $REPO $APP_DIR
    cd $APP_DIR
fi

# Stop old container if running
docker compose down --remove-orphans 2>/dev/null || true

# Build and start
echo "Building Docker image..."
docker compose build --no-cache

echo "Starting container..."
docker compose up -d

echo ""
echo "=== Deployed! ==="
echo "App running on port 8001"
echo "Check status: docker compose logs -f"
docker compose ps
