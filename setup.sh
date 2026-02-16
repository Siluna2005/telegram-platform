#!/bin/bash

echo "🚀 Telegram Media Platform - Setup Script"
echo "=========================================="

# Update system
echo "📦 Updating system..."
sudo apt update && sudo apt upgrade -y

# Install Python
echo "🐍 Installing Python..."
sudo apt install -y python3 python3-pip python3-venv

# Install MongoDB
echo "📦 Installing MongoDB..."
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod

# Create project directory
echo "📁 Setting up project..."
cd ~
mkdir -p telegram-platform
cd telegram-platform

# Install Python packages
echo "📦 Installing Python packages..."
pip3 install --upgrade pip

# Backend
cd backend
pip3 install -r requirements.txt
cd ..

# Bots
for bot in storage_bot control_bot streaming_bot; do
    cd bots/$bot
    pip3 install -r requirements.txt
    cd ../..
done

# Copy environment file
echo "⚙️  Creating .env file..."
cp .env.example .env
echo "⚠️  IMPORTANT: Edit .env file with your configuration!"

# Setup systemd services
echo "🔧 Setting up systemd services..."
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file: nano .env"
echo "2. Create Telegram bots with @BotFather"
echo "3. Create storage channel and add bots"
echo "4. Start services:"
echo "   sudo systemctl start telegram-backend"
echo "   sudo systemctl start telegram-storage-bot"
echo "   sudo systemctl start telegram-control-bot"
echo "   sudo systemctl start telegram-streaming-bot"
echo "5. Enable auto-start:"
echo "   sudo systemctl enable telegram-backend"
echo "   sudo systemctl enable telegram-storage-bot"
echo "   sudo systemctl enable telegram-control-bot"
echo "   sudo systemctl enable telegram-streaming-bot"