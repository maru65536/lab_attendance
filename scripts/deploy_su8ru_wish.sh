#!/bin/bash

# su8ru wishlist watcher deployment script
# Syncs watcher code to EC2 and provisions systemd timer for daily execution

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
APP_ROOT="$REPO_ROOT/apps/su8ru_wish"
TERRAFORM_DIR="$REPO_ROOT/infra/server/terraform"

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
export AWS_PROFILE

EC2_HOST="${EC2_HOST:-$(terraform_output instance_public_ip)}"
SSH_KEY="$(expand_path "${SSH_KEY:-$HOME/.ssh/id_ed25519}")"
REMOTE_WISHLIST_DIR="${REMOTE_WISHLIST_DIR:-/opt/wishlist}"
ENV_FILE="${ENV_FILE:-$REPO_ROOT/.env.su8ru_wish}"
REMOTE_ENV_PATH="${REMOTE_ENV_PATH:-$REMOTE_WISHLIST_DIR/.env}"
STATE_DIR="${STATE_DIR:-/var/lib/wishlist}"
STATE_FILENAME="${STATE_FILENAME:-state_friend.json}"
SERVICE_NAME="${SERVICE_NAME:-su8ru_wish}"
SYSTEM_USER="${SYSTEM_USER:-ubuntu}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ -z "$EC2_HOST" ]; then
  echo "❌ EC2_HOST is empty. Provide EC2_HOST or ensure terraform outputs are available." >&2
  exit 1
fi

if [ ! -f "$SSH_KEY" ]; then
  echo "❌ SSH key not found at $SSH_KEY" >&2
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ Env file not found: $ENV_FILE" >&2
  echo "   Copy .env.su8ru_wish.example to .env.su8ru_wish and set WEBHOOK_URL."
  exit 1
fi

# Load configuration from the env file while preserving existing exports
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

LIST_URL="${LIST_URL:-https://www.amazon.co.jp/hz/wishlist/ls/20XG7YB46EBUX}"
WEBHOOK_URL="${WEBHOOK_URL:-}"
STATE_DIR="${STATE_DIR:-/var/lib/wishlist}"
STATE_FILENAME="${STATE_FILENAME:-state_friend.json}"
RUN_BASELINE="${RUN_BASELINE:-true}"

if [ -z "$WEBHOOK_URL" ]; then
  echo "❌ WEBHOOK_URL is not set in $ENV_FILE" >&2
  exit 1
fi

echo "🚀 Deploying su8ru wishlist watcher to $EC2_HOST..."

# Ensure remote directories exist and ownership is correct
echo "📁 Preparing remote directories..."
ssh -i "$SSH_KEY" ubuntu@"$EC2_HOST" "sudo mkdir -p '$REMOTE_WISHLIST_DIR' '$STATE_DIR' && sudo chown -R $SYSTEM_USER:$SYSTEM_USER '$REMOTE_WISHLIST_DIR' '$STATE_DIR'"

# Upload env configuration securely (avoid storing secrets in service unit)
echo "🔐 Uploading environment config..."
scp -i "$SSH_KEY" "$ENV_FILE" "ubuntu@$EC2_HOST:${REMOTE_ENV_PATH}" >/dev/null
ssh -i "$SSH_KEY" ubuntu@"$EC2_HOST" "chmod 600 '$REMOTE_ENV_PATH'"

# Sync application files
echo "📦 Uploading watcher code..."
rsync -avz -e "ssh -i $SSH_KEY" \
  --delete \
  --exclude '.env' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude '.venv' \
  "$APP_ROOT/" "ubuntu@$EC2_HOST:$REMOTE_WISHLIST_DIR/"

echo "🐍 Setting up Python environment and systemd units..."
ssh -i "$SSH_KEY" ubuntu@"$EC2_HOST" \
  "REMOTE_WISHLIST_DIR='$REMOTE_WISHLIST_DIR' STATE_DIR='$STATE_DIR' STATE_FILENAME='$STATE_FILENAME' SERVICE_NAME='$SERVICE_NAME' SYSTEM_USER='$SYSTEM_USER' LIST_URL='$LIST_URL' REMOTE_ENV_PATH='$REMOTE_ENV_PATH' RUN_BASELINE='$RUN_BASELINE' PYTHON_BIN='$PYTHON_BIN' bash -s" <<'EOF_REMOTE'
set -euo pipefail

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "❌ ${PYTHON_BIN} not found on remote host" >&2
  exit 2
fi

if ! "${PYTHON_BIN}" -m venv --help >/dev/null 2>&1; then
  echo "📦 Installing python3-venv support..."
  sudo apt-get update -y
  sudo apt-get install -y python3-venv
fi

cd "$REMOTE_WISHLIST_DIR"

if [ ! -f "$REMOTE_ENV_PATH" ]; then
  echo "❌ Environment file not found at $REMOTE_ENV_PATH" >&2
  exit 3
fi

if [ ! -d ".venv" ]; then
  "${PYTHON_BIN}" -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install "requests>=2.31.0" "beautifulsoup4>=4.12.0"
deactivate

SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
TIMER_PATH="/etc/systemd/system/${SERVICE_NAME}.timer"

sudo tee "$SERVICE_PATH" >/dev/null <<SERVICE_UNIT
[Unit]
Description=Amazon wishlist watcher (su8ru)
After=network.target

[Service]
Type=oneshot
User=${SYSTEM_USER}
Group=${SYSTEM_USER}
WorkingDirectory=${REMOTE_WISHLIST_DIR}
EnvironmentFile=${REMOTE_ENV_PATH}
Environment=STATE_DIR=${STATE_DIR}
Environment=STATE_FILENAME=${STATE_FILENAME}
ExecStart=${REMOTE_WISHLIST_DIR}/.venv/bin/python ${REMOTE_WISHLIST_DIR}/watcher.py
SuccessExitStatus=0

[Install]
WantedBy=multi-user.target
SERVICE_UNIT

sudo tee "$TIMER_PATH" >/dev/null <<TIMER_UNIT
[Unit]
Description=Run su8ru wishlist watcher daily (JST 09:00)

[Timer]
OnCalendar=*-*-* 09:00:00 Asia/Tokyo
Persistent=true
Unit=${SERVICE_NAME}.service

[Install]
WantedBy=timers.target
TIMER_UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now "${SERVICE_NAME}.timer"

echo "✅ systemd timer enabled"

if [ "${RUN_BASELINE}" = "true" ]; then
  echo "📊 Capturing baseline state..."
  sudo -u "$SYSTEM_USER" bash <<BASELINE || true
set -euo pipefail
set -a
source "$REMOTE_ENV_PATH"
set +a
export LIST_URL="${LIST_URL}"
export STATE_DIR="${STATE_DIR}"
export STATE_FILENAME="${STATE_FILENAME}"
export BASELINE_ONLY=true
"${REMOTE_WISHLIST_DIR}/.venv/bin/python" "${REMOTE_WISHLIST_DIR}/watcher.py"
BASELINE
fi
EOF_REMOTE

echo "🎯 Deployment finished."
echo "ℹ️  Verify timer: ssh -i $SSH_KEY ubuntu@$EC2_HOST 'systemctl list-timers | grep $SERVICE_NAME'"
echo "ℹ️  Run once manually: ssh -i $SSH_KEY ubuntu@$EC2_HOST 'sudo systemctl start ${SERVICE_NAME}.service'"
echo "ℹ️  Inspect logs: ssh -i $SSH_KEY ubuntu@$EC2_HOST 'journalctl -u ${SERVICE_NAME}.service --since "1 day ago"'"
