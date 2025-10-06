#!/bin/bash

# Lab Attendance App Deployment Script with Domain Support
# This script deploys the application to AWS EC2 with nginx reverse proxy

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
APP_ROOT="$REPO_ROOT/apps/lab-attendance"
TERRAFORM_DIR="$REPO_ROOT/infra/server/terraform"
SITE_ROOT="$REPO_ROOT/site-root"

terraform_output() {
  (cd "$TERRAFORM_DIR" && terraform output -raw "$1" 2>/dev/null)
}

expand_path() {
  case "$1" in
    ~*) echo "${1/#\~/$HOME}" ;;
    *) echo "$1" ;;
  esac
}

AWS_PROFILE="${AWS_PROFILE:-lab-migration}"
BACKUP_BUCKET="${BACKUP_BUCKET:-lab-attendance-backups}"
CRON_REGION="${CRON_REGION:-ap-northeast-1}"

export AWS_PROFILE

export TF_VAR_backup_bucket_name="$BACKUP_BUCKET"

echo "🛠  Running terraform (bucket: $BACKUP_BUCKET)..."
terraform -chdir="$TERRAFORM_DIR" init -input=false
terraform -chdir="$TERRAFORM_DIR" apply -input=false -auto-approve

EC2_HOST="${EC2_HOST:-$(terraform_output instance_public_ip)}"
SSH_KEY="$(expand_path "${SSH_KEY:-$HOME/.ssh/id_ed25519}")"
REMOTE_APP_DIR="${REMOTE_APP_DIR:-/home/ubuntu/lab_attendance}"
REMOTE_SITE_DIR="${REMOTE_SITE_DIR:-/var/www/html}"
DOMAIN="${DOMAIN:-$(terraform_output domain_name)}"

if [ -z "$DOMAIN" ]; then
  DOMAIN="maru65536.com"
fi

if [ -z "$EC2_HOST" ]; then
  echo "❌ EC2_HOST is empty. Ensure Terraform has been applied or set EC2_HOST manually." >&2
  exit 1
fi

echo "🚀 Starting deployment to EC2 with domain support..."

ssh -i "$SSH_KEY" ubuntu@$EC2_HOST "mkdir -p $REMOTE_APP_DIR/backend $REMOTE_APP_DIR/frontend"
ssh -i "$SSH_KEY" ubuntu@$EC2_HOST "sudo mkdir -p $REMOTE_SITE_DIR && sudo chown ubuntu:ubuntu $REMOTE_SITE_DIR"

# Copy backend files (excluding Python cache and venv)
echo "📦 Uploading backend files..."
echo "Start time: $(date)"
rsync -avz -e "ssh -i $SSH_KEY" --exclude '__pycache__' --exclude '.venv' --exclude '*.pyc' --exclude '.git' "$APP_ROOT/backend/" ubuntu@$EC2_HOST:$REMOTE_APP_DIR/backend/
echo "Backend upload completed: $(date)"

# Copy frontend files (excluding node_modules and .next)
echo "📦 Uploading frontend files..."
rsync -avz -e "ssh -i $SSH_KEY" --exclude 'node_modules' --exclude '.next' --exclude '.git' "$APP_ROOT/frontend/" ubuntu@$EC2_HOST:$REMOTE_APP_DIR/frontend/

# Copy nginx configuration
echo "📦 Uploading nginx configuration..."
scp -i $SSH_KEY "$APP_ROOT/nginx-maru65536.conf" ubuntu@$EC2_HOST:/tmp/

# Deploy backend
echo "🐍 Setting up backend..."
ssh -i $SSH_KEY ubuntu@$EC2_HOST "BACKUP_BUCKET='$BACKUP_BUCKET' REMOTE_APP_DIR='$REMOTE_APP_DIR' CRON_REGION='$CRON_REGION' bash -s" <<'EOF_BACKEND'
set -euo pipefail

cd "$REMOTE_APP_DIR/backend"
# Kill existing backend process
pkill -f "uvicorn main:app" || true

# Restore latest backup if available
if [ -n "${BACKUP_BUCKET:-}" ] && command -v aws >/dev/null 2>&1; then
    LATEST_OBJECT=$(aws s3 ls "s3://$BACKUP_BUCKET/backups/" --recursive --region "$CRON_REGION" 2>/dev/null | awk '{print $4}' | sort | tail -n 1)
    if [ -n "$LATEST_OBJECT" ]; then
        echo "📦 Restoring backup: $LATEST_OBJECT"
        aws s3 cp "s3://$BACKUP_BUCKET/$LATEST_OBJECT" attendance.db --region "$CRON_REGION" --quiet || echo "⚠️  Backup restore failed"
    else
        echo "ℹ️  No backup objects found in s3://$BACKUP_BUCKET/backups/"
    fi
fi

# Create and setup Python virtual environment
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install dependencies and start backend
pip install -r requirements.txt
nohup .venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 > /tmp/backend.log 2>&1 &
sleep 3
echo "Backend started on localhost:8000"

# Ensure cron entry exists for daily backup
if [ -n "${BACKUP_BUCKET:-}" ]; then
    CRON_LINE="10 0 * * * AWS_REGION=${CRON_REGION} /usr/bin/python3 ${REMOTE_APP_DIR}/backend/backup_to_s3.py --bucket ${BACKUP_BUCKET} --region ${CRON_REGION} --key backups/attendance-\$(date +\\%Y-\\%m-\\%d).db >> /var/log/lab-app/backup.log 2>&1"
    (crontab -l 2>/dev/null | grep -Fv "backup_to_s3.py"; echo "$CRON_LINE") | crontab -
    echo "🕒 Cron job installed for daily S3 backup"
fi
EOF_BACKEND

# Deploy frontend
echo "⚛️  Setting up frontend..."
ssh -i $SSH_KEY ubuntu@$EC2_HOST "REMOTE_APP_DIR='$REMOTE_APP_DIR' bash -s" <<'EOF_FRONTEND'
cd "$REMOTE_APP_DIR/frontend"

# Kill existing frontend processes
pkill -f "next" || true

# Setup Node.js 20 LTS using NodeSource repository
if ! command -v node &> /dev/null || [ "$(node --version | cut -d'.' -f1 | cut -d'v' -f2)" -lt "20" ]; then
    echo "Installing Node.js 20 LTS..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# Install dependencies and build frontend
cd "$REMOTE_APP_DIR/frontend"
rm -rf node_modules package-lock.json .next
npm install
npm run build
nohup npm run start -- -H 127.0.0.1 -p 3000 > /tmp/frontend.log 2>&1 &
sleep 5
echo "Frontend built and started on localhost:3000"
EOF_FRONTEND

# Setup nginx
echo "🌐 Setting up nginx..."
ssh -i $SSH_KEY ubuntu@$EC2_HOST << 'EOF_NGINX'
# Install nginx if not already installed
if ! command -v nginx &> /dev/null; then
    sudo apt update -y
    sudo apt install -y nginx
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

# Sync root static site if present
if [ -d "$SITE_ROOT" ]; then
  echo "🗂  Uploading root static site..."
  rsync -avz -e "ssh -i $SSH_KEY" --delete "$SITE_ROOT/" ubuntu@$EC2_HOST:$REMOTE_SITE_DIR/
fi

echo "✅ Deployment completed!"
echo "🌐 Root menu: http://$DOMAIN/"
echo "🌐 Lab Attendance: http://$DOMAIN/lab_attendance/"
echo "🔧 API: http://$DOMAIN/lab_attendance/api/status"
echo ""
echo "📱 iPhone URLs:"
echo "  入室: http://$DOMAIN/lab_attendance/api/lab-entry?action=enter"
echo "  退室: http://$DOMAIN/lab_attendance/api/lab-entry?action=exit"
echo ""
echo "📊 Check status:"
echo "  ssh -i $SSH_KEY ubuntu@$EC2_HOST 'ps aux | grep -E \"(uvicorn|next)\" | grep -v grep'"
echo "  ssh -i $SSH_KEY ubuntu@$EC2_HOST 'sudo systemctl status nginx'"
