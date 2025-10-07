#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
BACKEND_DIR="${REPO_ROOT}/apps/kbd-ir/backend"
FRONTEND_DIR="${REPO_ROOT}/apps/kbd-ir/frontend"
REMOTE_HOST=${REMOTE_HOST:-""}
REMOTE_PATH=${REMOTE_PATH:-"/var/www/kbd-ir"}
PYTHON_BIN=${PYTHON_BIN:-"python3"}
NODE_BIN=${NODE_BIN:-"npm"}

if [[ -z "${REMOTE_HOST}" ]]; then
  echo "REMOTE_HOST is required (e.g., user@example.com)" >&2
  exit 1
fi

echo "[1/5] Building frontend"
cd "${FRONTEND_DIR}"
${NODE_BIN} install
${NODE_BIN} run build

echo "[2/5] Preparing backend virtual environment"
cd "${BACKEND_DIR}"
${PYTHON_BIN} -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [[ -f "alembic.ini" ]]; then
  echo "[3/5] Running database migrations"
  alembic upgrade head
else
  echo "[3/5] Skipping migrations (alembic.ini not found)"
fi

echo "[4/5] Syncing application to ${REMOTE_HOST}:${REMOTE_PATH}"
rsync -avz --delete \
  "${BACKEND_DIR}/" "${REMOTE_HOST}:${REMOTE_PATH}/backend/"
rsync -avz --delete \
  "${FRONTEND_DIR}/.next/" "${REMOTE_HOST}:${REMOTE_PATH}/frontend/.next/"
rsync -avz --delete \
  "${FRONTEND_DIR}/package.json" "${REMOTE_HOST}:${REMOTE_PATH}/frontend/"
rsync -avz --delete \
  "${FRONTEND_DIR}/next.config.js" "${REMOTE_HOST}:${REMOTE_PATH}/frontend/"

echo "[5/5] Restarting services"
ssh "${REMOTE_HOST}" "cd ${REMOTE_PATH} && ./scripts/restart_kbd_ir.sh"

echo "Deployment completed."
