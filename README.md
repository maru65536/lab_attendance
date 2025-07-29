# Lab Attendance App

研究室滞在時間を可視化するWebアプリケーション

## 構成

- **Backend**: FastAPI + SQLite
- **Frontend**: Next.js 10.2.3 + React 17 + TypeScript
- **Infrastructure**: AWS EC2 (t2.micro) + Terraform

## iPhone連携

iPhoneのショートカットアプリから以下のURLにGETリクエストを送信：

- 入室: `http://maru65536.com/lab_attendance/api/lab-entry?action=enter`
- 退室: `http://maru65536.com/lab_attendance/api/lab-entry?action=exit`

## デプロイ

### 一発デプロイ
```bash
./deploy.sh
```

### 手動デプロイ

#### インフラ構築 (初回のみ)
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

#### アプリケーションデプロイ
```bash
# Backend
scp -i ~/.ssh/id_ed25519 -r backend/ ec2-user@3.115.30.125:/home/ec2-user/lab_attendance/
ssh -i ~/.ssh/id_ed25519 ec2-user@3.115.30.125
cd lab_attendance/backend
pip3 install --user -r requirements.txt
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &

# Frontend
scp -i ~/.ssh/id_ed25519 -r frontend/ ec2-user@3.115.30.125:/home/ec2-user/lab_attendance/
ssh -i ~/.ssh/id_ed25519 ec2-user@3.115.30.125
cd lab_attendance/frontend
PATH=/usr/local/node/bin:$PATH npm install --no-optional
PATH=/usr/local/node/bin:$PATH nohup npm run dev > /tmp/frontend.log 2>&1 &
```

## アクセス

- **Website**: http://maru65536.com/lab_attendance/
- **API**: http://maru65536.com/lab_attendance/api/status

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

### ログ確認
```bash
ssh -i ~/.ssh/id_ed25519 ec2-user@3.115.30.125 'tail -f /tmp/backend.log'
ssh -i ~/.ssh/id_ed25519 ec2-user@3.115.30.125 'tail -f /tmp/frontend.log'
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

