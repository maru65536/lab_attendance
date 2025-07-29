#!/bin/bash

# デプロイスクリプト
set -e

echo "🚀 研究室滞在時間アプリのデプロイを開始します..."

# 変数設定
APP_DIR="/var/www/lab-app"
REPO_URL="https://github.com/$1/lab-attendance-app.git"  # GitHubユーザー名を引数で受け取る
BACKEND_SERVICE="lab-attendance-backend"
FRONTEND_SERVICE="lab-attendance-frontend"

# 既存のアプリケーションを停止
echo "📦 既存のサービスを停止します..."
sudo systemctl stop $BACKEND_SERVICE 2>/dev/null || true
sudo systemctl stop $FRONTEND_SERVICE 2>/dev/null || true

# ディレクトリの準備
if [ -d "$APP_DIR" ]; then
    echo "🔄 既存のアプリケーションを更新します..."
    cd $APP_DIR
    git pull origin main
else
    echo "📥 アプリケーションをクローンします..."
    sudo mkdir -p $APP_DIR
    sudo chown ec2-user:ec2-user $APP_DIR
    git clone $REPO_URL $APP_DIR
    cd $APP_DIR
fi

# バックエンドのセットアップ
echo "🐍 バックエンドをセットアップします..."
cd $APP_DIR/backend
pip3 install --user -r requirements.txt

# フロントエンドのセットアップ
echo "⚛️ フロントエンドをセットアップします..."
cd $APP_DIR/frontend

# Node.jsのパスを設定
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 16

# 本番用の設定でnext.config.jsを更新
cat > next.config.js << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
  output: 'standalone',
}

module.exports = nextConfig
EOF

npm install
npm run build

# systemdサービスファイルの作成
echo "⚙️ systemdサービスを設定します..."

# バックエンドサービス
sudo tee /etc/systemd/system/$BACKEND_SERVICE.service > /dev/null << EOF
[Unit]
Description=Lab Attendance Backend API
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=$APP_DIR/backend
Environment=PATH=/home/ec2-user/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/ec2-user/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# フロントエンドサービス
sudo tee /etc/systemd/system/$FRONTEND_SERVICE.service > /dev/null << EOF
[Unit]
Description=Lab Attendance Frontend
After=network.target
Requires=$BACKEND_SERVICE.service

[Service]
Type=simple
User=ec2-user
WorkingDirectory=$APP_DIR/frontend
Environment=PATH=/home/ec2-user/.nvm/versions/node/v16.20.2/bin:/usr/local/bin:/usr/bin:/bin
Environment=NODE_ENV=production
ExecStart=/home/ec2-user/.nvm/versions/node/v16.20.2/bin/npm start
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# systemdの設定を再読み込み
sudo systemctl daemon-reload

# サービスを有効化して開始
echo "🔄 サービスを開始します..."
sudo systemctl enable $BACKEND_SERVICE
sudo systemctl enable $FRONTEND_SERVICE
sudo systemctl start $BACKEND_SERVICE
sudo systemctl start $FRONTEND_SERVICE

# ステータス確認
echo "✅ デプロイ完了！サービス状況を確認します..."
sleep 3
sudo systemctl status $BACKEND_SERVICE --no-pager -l
sudo systemctl status $FRONTEND_SERVICE --no-pager -l

echo "🎉 デプロイが完了しました！"
echo "📝 バックエンドAPI: http://localhost:8000"
echo "🌐 フロントエンド: http://localhost:3000"
echo ""
echo "ログ確認コマンド:"
echo "  バックエンド: sudo journalctl -u $BACKEND_SERVICE -f"
echo "  フロントエンド: sudo journalctl -u $FRONTEND_SERVICE -f"