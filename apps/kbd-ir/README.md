# KBD-IR

音楽ゲーム大会管理システムのバックエンド (FastAPI) とフロントエンド (Next.js) 実装です。

## Backend
- パス: `apps/kbd-ir/backend`
- フレームワーク: FastAPI + SQLAlchemy + SQLite (デフォルト)
- 主要エントリポイント: `main.py`
- 依存インストール: `pip install -r requirements.txt`
- ローカル起動: `uvicorn main:app --reload --port 8100`
- `.env`（任意）で `KBDIR_SECRET_KEY`, `KBDIR_DATABASE_URL`, `KBDIR_S3_BUCKET` などを設定

## Frontend
- パス: `apps/kbd-ir/frontend`
- フレームワーク: Next.js + React Query
- 依存インストール: `npm install`
- 開発サーバ: `npm run dev` (ポート3100)
- `NEXT_PUBLIC_KBDIR_API` 環境変数でAPIベースURLを指定（未指定時は `/api/kbd_ir`）

## デプロイ
- `scripts/deploy_kbd_ir.sh` で手動デプロイを想定
  - `REMOTE_HOST`, `REMOTE_PATH` を環境変数で指定
  - フロントビルド → バックエンド依存インストール → (必要に応じて) Alembic → rsync で同期 → リモート再起動

## インフラ
- Terraform (`infra/server/terraform/kbd_ir.tf`) で S3 バケットと SES ドメイン認証を管理
- バケット名やドメインは `variables.tf` で調整可

## テスト
- Backend: pytest テンプレートを追加予定（`apps/kbd-ir/backend/tests/`）
- Frontend: `npm test` で Jest + Testing Library のスモークテストを実行
