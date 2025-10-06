# Lab Attendance App

研究室滞在時間を可視化するWebアプリケーション

## 現在の状態

✅ **稼働中**: https://maru65536.com/lab_attendance/  
✅ **iPhone連携**: ショートカットアプリ対応  
✅ **自動更新**: 30秒ごとにリアルタイム更新  
✅ **進行中セッション**: 在室中は現在時刻までのバー表示  
✅ **モバイル対応**: iOS Safariでも安定動作

## 構成

- **Backend**: FastAPI + SQLite
- **Frontend**: Next.js 14 + React 18 + TypeScript
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
- S3 バケット（例: `lab-attendance-backups`）を作成済みで、`terraform/terraform.tfvars` で `backup_bucket_name` を設定

必要に応じて `terraform/terraform.tfvars` を作成し、`admin_cidr_blocks` や `instance_type` などを環境に合わせて上書きしてください。

### 一発デプロイ
```bash
./scripts/deploy_lab_attendance.sh
```

`scripts/deploy_lab_attendance.sh` は実行時に `infra/server/terraform` で `terraform init` / `terraform apply` を実行し、`BACKUP_BUCKET`（未指定時は `lab-attendance-backups`）を `TF_VAR_backup_bucket_name` として Terraform に伝えます。AWS プロファイルは既定で `lab-migration` を使用しますが、必要に応じて `AWS_PROFILE=<profile>` で上書きできます。バックエンド展開時には S3 バケットの `backups/` 以下から最新の `attendance-YYYY-MM-DD.db` を検出して自動復元し、同時に日次バックアップ用の cron エントリも idempotent に設定します。`CRON_REGION` を指定すると cron が使用する `AWS_REGION` を上書きできます（既定は `ap-northeast-1`）。また、リポジトリ直下の `site-root/` が存在する場合は `/var/www/html/` に同期され、トップページのメニューも更新されます。

### 手動デプロイ

#### 1. インフラ構築 (初回のみ)
```bash
export AWS_PROFILE=lab-migration
cd ../../infra/server/terraform
terraform init
terraform plan
terraform apply
```

**注意**: `terraform output`でEC2のIPアドレスを確認し、以下の手順で使用してください。

#### 2. アプリケーションデプロイ

**現行EC2 IP**: Terraformの `instance_public_ip` 出力を参照

# Terraformで払い出されたIPを取得
IP=$(cd ../../infra/server/terraform && terraform output -raw instance_public_ip)

```bash
# Backend
scp -i ~/.ssh/id_ed25519 -r apps/lab-attendance/backend/ ubuntu@$IP:/home/ubuntu/lab_attendance/
ssh -i ~/.ssh/id_ed25519 ubuntu@$IP << 'EOF'
cd lab_attendance/backend
pkill -f "uvicorn main:app" || true
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
nohup .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 > /tmp/backend.log 2>&1 &
EOF

# Frontend
scp -i ~/.ssh/id_ed25519 -r apps/lab-attendance/frontend/ ubuntu@$IP:/home/ubuntu/lab_attendance/
ssh -i ~/.ssh/id_ed25519 ubuntu@$IP << 'EOF'
cd lab_attendance/frontend
pkill -f "next" || true
rm -rf .next node_modules
npm install
npm run build
nohup npm run start -- -H 127.0.0.1 -p 3000 > /tmp/frontend.log 2>&1 &
EOF

# Nginx (初回のみ)
scp -i ~/.ssh/id_ed25519 nginx-maru65536.conf ubuntu@$IP:/tmp/
ssh -i ~/.ssh/id_ed25519 ubuntu@$IP << 'EOF'
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

- Node.js 20 LTS を推奨
- Next.js 14 / React 18 を基準環境に統一

## トラブルシューティング

```bash
IP=$(cd terraform && terraform output -raw instance_public_ip)
```

### プロセス確認
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@$IP 'ps aux | grep -E "(uvicorn|next)" | grep -v grep'
```

### ポート確認
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@$IP 'netstat -tlnp | grep -E ":(3000|8000)"'
```

### サービス状態確認
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@$IP 'sudo systemctl status nginx'
curl -I https://maru65536.com/lab_attendance/
curl https://maru65536.com/lab_attendance/api/status
```

### ログ確認
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@$IP 'tail -f /tmp/backend.log'
ssh -i ~/.ssh/id_ed25519 ubuntu@$IP 'tail -f /tmp/frontend.log'
ssh -i ~/.ssh/id_ed25519 ubuntu@$IP 'sudo tail -f /var/log/nginx/error.log'
```

### よくある問題と対処法

#### Node.js バージョン問題
```bash
# Node.js 20 LTS インストール確認
ssh -i ~/.ssh/id_ed25519 ubuntu@$IP 'node --version'

# 手動インストール（必要に応じて）
ssh -i ~/.ssh/id_ed25519 ubuntu@$IP << 'EOF'
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
EOF
```

#### フロントエンドキャッシュ問題
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@$IP << 'EOF'
cd lab_attendance/frontend
pkill -f "next" || true
rm -rf .next node_modules
npm install
npm run build
nohup npm run start -- -H 127.0.0.1 -p 3000 > /tmp/frontend.log 2>&1 &
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

### デイリーバックアップ
1. S3 にバケットを作成し、IAM ロールから書き込めるよう許可（例: `lab-attendance-backups`）。
2. EC2 にアタッチしている IAM ロールで S3 への `PutObject`/`GetObject` を許可。
3. 以下を crontab へ追加して日次バックアップを実行（例では UTC 0:05 に実行）。
   ```bash
   AWS_REGION=ap-northeast-1 AWS_PROFILE=lab-migration \
   S3_BUCKET=lab-attendance-backups \ 
   /usr/bin/python3 /home/ubuntu/lab_attendance/backend/backup_to_s3.py \
     --bucket $S3_BUCKET --region $AWS_REGION --key backups/attendance-$(date +\%Y-\%m-\%d).db
   ```
4. 復元時には `aws s3 cp s3://$S3_BUCKET/backups/attendance-2025-10-06.db attendance.db` のようにダウンロードしてから FastAPI を再起動。

### EC2 ロールの設定
1. CloudWatch -> EC2 -> 「IAM ロール」を確認し、使用中のロール名（例: `lab-attendance-ec2-role`）を控える
2. 以下のポリシーを作成（AWS CLI またはコンソール）
   ```bash
   cat <<'POLICY' > /tmp/lab-attendance-s3-policy.json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:GetObject",
           "s3:PutObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::lab-attendance-backups",
           "arn:aws:s3:::lab-attendance-backups/*"
         ]
       }
     ]
   }
   POLICY

   aws iam create-policy \
     --policy-name LabAttendanceS3Backup \
     --policy-document file:///tmp/lab-attendance-s3-policy.json
   ```
3. ロールへポリシーをアタッチ
   ```bash
   aws iam attach-role-policy \
     --role-name lab-attendance-ec2-role \
     --policy-arn arn:aws:iam::<アカウントID>:policy/LabAttendanceS3Backup
   ```

ロールに S3 バケットへのアクセス権限が付与されたら、サーバー上で `aws sts get-caller-identity` が成功することを確認し、バックアップスクリプトを実行できます。
