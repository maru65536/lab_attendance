#!/bin/bash

# Lab Attendance App Deployment Script with Domain Support
# This script deploys the application to AWS EC2 with nginx reverse proxy

set -e

EC2_HOST="3.115.30.125"
SSH_KEY="~/.ssh/id_ed25519"
REMOTE_DIR="/home/ec2-user/lab_attendance"
DOMAIN="maru65536.com"

echo "🚀 Starting deployment to EC2 with domain support..."

# Copy backend files
echo "📦 Uploading backend files..."
scp -i $SSH_KEY -r backend/ ec2-user@$EC2_HOST:$REMOTE_DIR/

# Copy frontend files
echo "📦 Uploading frontend files..."
scp -i $SSH_KEY -r frontend/ ec2-user@$EC2_HOST:$REMOTE_DIR/

# Copy nginx configuration
echo "📦 Uploading nginx configuration..."
scp -i $SSH_KEY nginx-maru65536.conf ec2-user@$EC2_HOST:/tmp/

# Deploy backend
echo "🐍 Setting up backend..."
ssh -i $SSH_KEY ec2-user@$EC2_HOST << 'EOF_BACKEND'
cd /home/ec2-user/lab_attendance/backend
# Kill existing backend process
pkill -f "uvicorn main:app" || true
# Install dependencies and start backend
pip3 install --user -r requirements.txt
nohup python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > /tmp/backend.log 2>&1 &
sleep 3
echo "Backend started on localhost:8000"
EOF_BACKEND

# Deploy frontend
echo "⚛️  Setting up frontend..."
ssh -i $SSH_KEY ec2-user@$EC2_HOST << 'EOF_FRONTEND'
cd /home/ec2-user/lab_attendance/frontend

# Kill existing frontend process
ps aux | grep 'next dev' | grep -v grep | awk '{print $2}' | xargs kill -9 || true

# Setup Node.js 12 if not already installed
if [ ! -d "/usr/local/node" ]; then
    echo "Installing Node.js 12.22.9..."
    cd /tmp
    wget -q https://nodejs.org/download/release/v12.22.9/node-v12.22.9-linux-x64.tar.gz
    tar -xzf node-v12.22.9-linux-x64.tar.gz
    sudo mkdir -p /usr/local/node
    sudo mv node-v12.22.9-linux-x64/* /usr/local/node/
    rm -f node-v12.22.9-linux-x64.tar.gz
fi

# Install dependencies and start frontend
cd /home/ec2-user/lab_attendance/frontend
rm -rf node_modules package-lock.json
PATH=/usr/local/node/bin:$PATH npm install --no-optional
PATH=/usr/local/node/bin:$PATH nohup npm run dev -- -H 127.0.0.1 > /tmp/frontend.log 2>&1 &
sleep 5
echo "Frontend started on localhost:3000"
EOF_FRONTEND

# Setup nginx
echo "🌐 Setting up nginx..."
ssh -i $SSH_KEY ec2-user@$EC2_HOST << 'EOF_NGINX'
# Install nginx if not already installed
if ! command -v nginx &> /dev/null; then
    sudo yum update -y
    sudo amazon-linux-extras install nginx1 -y
fi

# Copy nginx configuration
sudo cp /tmp/nginx-maru65536.conf /etc/nginx/conf.d/
sudo rm -f /tmp/nginx-maru65536.conf

# Test nginx configuration
sudo nginx -t

# Start and enable nginx
sudo systemctl start nginx
sudo systemctl enable nginx
sudo systemctl reload nginx

echo "Nginx configured and started"
EOF_NGINX

echo "✅ Deployment completed!"
echo "🌐 Website: http://$DOMAIN/lab_attendance/"
echo "🔧 API: http://$DOMAIN/lab_attendance/api/status"
echo ""
echo "📱 iPhone URLs:"
echo "  入室: http://$DOMAIN/lab_attendance/api/lab-entry?action=enter"
echo "  退室: http://$DOMAIN/lab_attendance/api/lab-entry?action=exit"
echo ""
echo "📊 Check status:"
echo "  ssh -i $SSH_KEY ec2-user@$EC2_HOST 'ps aux | grep -E \"(uvicorn|next)\" | grep -v grep'"
echo "  ssh -i $SSH_KEY ec2-user@$EC2_HOST 'sudo systemctl status nginx'"