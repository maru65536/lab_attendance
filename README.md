# 研究室滞在時間可視化アプリ

iPhoneからの入室・退室通知を受け取り、研究室滞在時間を可視化するWebアプリケーション

## システム構成

- **Backend**: FastAPI (Python)
- **Frontend**: Next.js (React/TypeScript)
- **Database**: SQLite
- **Infrastructure**: AWS EC2
- **Web Server**: nginx
- **Domain**: maru65536.com

## 機能

### API機能
- `/api/lab-entry` - 入退室記録（POST/GET両対応）
- `/api/attendance-data` - 滞在データ取得
- `/api/status` - 現在の在室状況

### フロントエンド機能
- 30日×24時間のヒートマップ表示
- リアルタイム在室状況表示
- レスポンシブデザイン

## デプロイ方法

### 1. EC2インスタンスでの初回デプロイ

```bash
# GitHubからクローン（ユーザー名を指定）
cd /home/ec2-user
git clone https://github.com/YOUR_USERNAME/lab-attendance-app.git
cd lab-attendance-app

# デプロイスクリプトを実行
chmod +x scripts/deploy.sh
./scripts/deploy.sh YOUR_USERNAME
```

### 2. nginx設定

```bash
# nginx設定ファイルをコピー
sudo cp nginx/lab-attendance.conf /etc/nginx/conf.d/
sudo nginx -t
sudo systemctl restart nginx
```

### 3. SSL証明書設定（Let's Encrypt）

```bash
# certbotのインストール
sudo yum install -y certbot python3-certbot-nginx

# SSL証明書取得
sudo certbot --nginx -d maru65536.com

# 自動更新設定
sudo crontab -e
# 以下を追加：
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## 開発環境

### Backend開発

```bash
cd backend
pip3 install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend開発

```bash
cd frontend
npm install
npm run dev
```

## API使用例

### iPhone Shortcutsアプリから入室記録

```bash
# GET方式
curl "http://maru65536.com/api/lab-entry?action=enter"

# POST方式
curl -X POST "http://maru65536.com/api/lab-entry" \
     -H "Content-Type: application/json" \
     -d '{"action": "enter"}'
```

### 退室記録

```bash
curl "http://maru65536.com/api/lab-entry?action=exit"
```

## ディレクトリ構造

```
lab-attendance-app/
├── backend/
│   ├── main.py              # FastAPIアプリケーション
│   ├── requirements.txt     # Python依存関係
│   └── attendance.db        # SQLiteデータベース（自動生成）
├── frontend/
│   ├── pages/
│   │   ├── _app.tsx
│   │   └── index.tsx        # メインページ
│   ├── styles/
│   │   └── globals.css      # スタイルシート
│   ├── package.json
│   ├── tsconfig.json
│   └── next.config.js
├── scripts/
│   └── deploy.sh            # デプロイスクリプト
├── nginx/
│   └── lab-attendance.conf  # nginx設定
└── README.md
```

## サービス管理

### サービス状況確認

```bash
sudo systemctl status lab-attendance-backend
sudo systemctl status lab-attendance-frontend
```

### ログ確認

```bash
# バックエンドログ
sudo journalctl -u lab-attendance-backend -f

# フロントエンドログ
sudo journalctl -u lab-attendance-frontend -f

# nginxログ
sudo tail -f /var/log/nginx/lab-attendance.access.log
```

### サービス再起動

```bash
sudo systemctl restart lab-attendance-backend
sudo systemctl restart lab-attendance-frontend
sudo systemctl reload nginx
```

## トラブルシューティング

### よくある問題

1. **Node.jsが見つからない**
   ```bash
   source ~/.bashrc
   nvm use 16
   ```

2. **ポートが使用中**
   ```bash
   sudo lsof -i :8000
   sudo lsof -i :3000
   ```

3. **データベースファイルのアクセス権限**
   ```bash
   chmod 644 /var/www/lab-app/backend/attendance.db
   ```

4. **nginxの設定エラー**
   ```bash
   sudo nginx -t
   sudo systemctl status nginx
   ```

## 開発者向け情報

### 重複アクション処理
- 連続する同じアクション（入室→入室、退室→退室）は無視
- データベースレベルでの整合性チェック

### データ形式
- タイムスタンプはサーバー側で自動生成
- SQLiteを使用した軽量なデータ管理

### セキュリティ
- CORS設定によるクロスオリジン制御
- nginxによるリバースプロキシ
- SSL/TLS暗号化（Let's Encrypt）

## ライセンス

MIT License