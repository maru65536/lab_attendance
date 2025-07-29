# Lab Attendance App

研究室滞在時間を可視化するWebアプリケーション

## 現在の状態

✅ **稼働中**: https://maru65536.com/lab_attendance/  
✅ **iPhone連携**: ショートカットアプリ対応  
✅ **自動更新**: 30秒ごとにリアルタイム更新  
✅ **進行中セッション**: 在室中は現在時刻までのバー表示  
🔧 **既知の問題**: スマホでの「e is not a function」エラー（PC・タブレットは正常動作）

## 構成

- **Backend**: FastAPI + SQLite
- **Frontend**: Next.js 10.2.3 + React 17 + TypeScript
- **Infrastructure**: AWS EC2 (t2.micro) + Terraform + nginx + Cloudflare SSL

## 機能

### 📊 可視化機能
- **横バー形式**: 1日の滞在時間を24時間軸の横バーで表示
- **30日分表示**: 過去30日間のデータを新しい日が上から表示
- **リアルタイム更新**: 30秒ごとに自動更新
- **進行中セッション**: 在室中は現在時刻までの緑色バーをリアルタイム表示
- **詳細ツールチップ**: バーにマウスオーバーで時刻・滞在時間を表示

### 📱 iPhone連携
- **ワンタップ入退室**: ショートカットアプリから簡単記録
- **重複防止**: 同じアクションの連続実行を自動で無視
- **即座反映**: 記録後すぐにWebで確認可能

### 🔧 技術的特徴
- **レスポンシブデザイン**: PC・タブレット・スマホ対応
- **JST表示**: 日本時間での正確な時刻表示
- **SQLite**: 軽量で高速なデータベース
- **SSL対応**: HTTPS接続でセキュア

## iPhone連携

iPhoneのショートカットアプリから以下のURLにGETリクエストを送信：

- 入室: `https://maru65536.com/lab_attendance/api/lab-entry?action=enter`
- 退室: `https://maru65536.com/lab_attendance/api/lab-entry?action=exit`

## デプロイ

### 前提条件
- AWS CLI設定済み
- Terraform インストール済み
- SSH鍵 (`~/.ssh/id_ed25519`) 設定済み
- Cloudflareでドメイン設定済み（SSL: Flexible モード）

### 一発デプロイ
```bash
./deploy.sh
```

### 手動デプロイ

#### 1. インフラ構築 (初回のみ)
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

**注意**: `terraform output`でEC2のIPアドレスを確認し、以下の手順で使用してください。

#### 2. アプリケーションデプロイ

**Current EC2 IP**: `3.115.30.125`

```bash
# Backend
scp -i ~/.ssh/id_ed25519 -r backend/ ec2-user@3.115.30.125:/home/ec2-user/lab_attendance/
ssh -i ~/.ssh/id_ed25519 ec2-user@3.115.30.125 << 'EOF'
cd lab_attendance/backend
pkill -f "uvicorn main:app" || true
pip3 install --user -r requirements.txt
nohup python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > /tmp/backend.log 2>&1 &
EOF

# Frontend
scp -i ~/.ssh/id_ed25519 -r frontend/ ec2-user@3.115.30.125:/home/ec2-user/lab_attendance/
ssh -i ~/.ssh/id_ed25519 ec2-user@3.115.30.125 << 'EOF'
cd lab_attendance/frontend
pkill -f "next dev" || true
rm -rf .next node_modules
PATH=/usr/local/node/bin:$PATH npm install --no-optional
PATH=/usr/local/node/bin:$PATH nohup npm run dev -- -H 127.0.0.1 > /tmp/frontend.log 2>&1 &
EOF

# Nginx (初回のみ)
scp -i ~/.ssh/id_ed25519 nginx-maru65536.conf ec2-user@3.115.30.125:/tmp/
ssh -i ~/.ssh/id_ed25519 ec2-user@3.115.30.125 << 'EOF'
sudo amazon-linux-extras install nginx1 -y
sudo cp /tmp/nginx-maru65536.conf /etc/nginx/conf.d/
sudo nginx -t
sudo systemctl start nginx
sudo systemctl enable nginx
EOF
```

## アクセス

- **Website**: https://maru65536.com/lab_attendance/
- **API**: https://maru65536.com/lab_attendance/api/status

## 開発環境の制約

- Node.js 12.22.9を使用（Amazon Linux 2のGLIBC制約のため）
- Next.js 10.2.3を使用（Node.js 12対応のため）
- React 17を使用（Next.js 10対応のため）

## トラブルシューティング

### プロセス確認
```bash
ssh -i ~/.ssh/id_ed25519 ec2-user@3.115.30.125 'ps aux | grep -E "(uvicorn|next)" | grep -v grep'
```

### ポート確認
```bash
ssh -i ~/.ssh/id_ed25519 ec2-user@3.115.30.125 'netstat -tlnp | grep -E ":(3000|8000)"'
```

### サービス状態確認
```bash
ssh -i ~/.ssh/id_ed25519 ec2-user@3.115.30.125 'sudo systemctl status nginx'
curl -I https://maru65536.com/lab_attendance/
curl https://maru65536.com/lab_attendance/api/status
```

### ログ確認
```bash
ssh -i ~/.ssh/id_ed25519 ec2-user@3.115.30.125 'tail -f /tmp/backend.log'
ssh -i ~/.ssh/id_ed25519 ec2-user@3.115.30.125 'tail -f /tmp/frontend.log'
ssh -i ~/.ssh/id_ed25519 ec2-user@3.115.30.125 'sudo tail -f /var/log/nginx/error.log'
```

### よくある問題と対処法

#### Node.js バージョン問題
```bash
# Node.js 12.22.9 インストール確認
ssh -i ~/.ssh/id_ed25519 ec2-user@3.115.30.125 '/usr/local/node/bin/node --version'

# 手動インストール（必要に応じて）
ssh -i ~/.ssh/id_ed25519 ec2-user@3.115.30.125 << 'EOF'
cd /tmp
wget https://nodejs.org/download/release/v12.22.9/node-v12.22.9-linux-x64.tar.gz
tar -xzf node-v12.22.9-linux-x64.tar.gz
sudo mkdir -p /usr/local/node
sudo mv node-v12.22.9-linux-x64/* /usr/local/node/
EOF
```

#### フロントエンドキャッシュ問題
```bash
ssh -i ~/.ssh/id_ed25519 ec2-user@3.115.30.125 << 'EOF'
cd lab_attendance/frontend
pkill -f "next dev" || true
rm -rf .next node_modules
PATH=/usr/local/node/bin:$PATH npm install --no-optional
PATH=/usr/local/node/bin:$PATH nohup npm run dev -- -H 127.0.0.1 > /tmp/frontend.log 2>&1 &
EOF
```

## API仕様

### POST /api/lab-entry
入退室記録を保存

**Request Body:**
```json
{
  "action": "enter" | "exit"
}
```

### GET /api/lab-entry?action=enter|exit
入退室記録を保存（iPhone用）

### GET /api/attendance-data?days=30
過去30日間の滞在データを取得

### GET /api/status
現在の滞在状況を取得

