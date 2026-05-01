#!/bin/bash
# Deploy Resume Parser to EC2
# Run from the project root directory on the EC2 instance

set -e

echo "=== Resume Parser EC2 Deployment ==="

# 1. Install system dependencies
echo "Installing system dependencies..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv

# 2. Create virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r backend/requirements.txt

# 4. Create required directories
mkdir -p linkedin_pdfs output manual_text photos

# 5. Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/resume-parser.service > /dev/null <<EOF
[Unit]
Description=Resume Parser Backend
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5
EnvironmentFile=$(pwd)/.env

[Install]
WantedBy=multi-user.target
EOF

# 6. Enable and start the service
echo "Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable resume-parser
sudo systemctl restart resume-parser

echo ""
echo "=== Deployment Complete ==="
echo "Backend running on port 8001"
echo "Check status: sudo systemctl status resume-parser"
echo "View logs: sudo journalctl -u resume-parser -f"
