# Maru65536 Web Stack

このリポジトリは、`maru65536.com` 上で動かす複数のコンテンツをまとめたモノレポ構成になっています。トップページ（`site-root/`）で各アプリへのハブを提供し、個別アプリは `apps/` 以下に配置しています。

## ディレクトリ構成

- `site-root/` — ルート (`/`) に表示する静的メニューページ。HTML/CSS を追加すればポートフォリオを簡単に拡張できます。
- `apps/lab-attendance/` — 研究室滞在時間トラッカー。FastAPI バックエンドと Next.js フロントエンドで構成。
- `infra/server/terraform/` — 共通サーバー（EC2・IAM ロール等）を管理する Terraform。
- `scripts/` — デプロイスクリプト群。現在は `deploy_lab_attendance.sh` のみ。
- `AGENTS.md` — コントリビューターガイド。

## ルートメニューページ

`site-root/index.html` と `site-root/styles.css` を編集すると、トップページのメニューを更新できます。`scripts/deploy_lab_attendance.sh` 実行時に `/var/www/html/` と同期されるため、リポジトリだけ更新しておけば再デプロイで反映されます。

## Lab Attendance アプリのデプロイ

Terraform とアプリデプロイ、S3 バックアップの復元・cron 登録までをワンステップで行うスクリプトを用意しています。

```bash
./scripts/deploy_lab_attendance.sh
```

- AWS プロファイルは既定で `lab-migration` を利用します。異なるプロファイルを使う場合は `AWS_PROFILE=<profile>` を付けてください。
- `BACKUP_BUCKET` を指定しない場合は `lab-attendance-backups` が使われます。
- `CRON_REGION` を指定すると、cron で使用する AWS リージョン (`AWS_REGION`) を上書きできます（既定は `ap-northeast-1`）。
- `REMOTE_APP_DIR` や `REMOTE_SITE_DIR` を上書きすれば別配置にも対応できます。

Terraform の詳細やバックアップ運用については `apps/lab-attendance/README.md` を参照してください。

## 追加アプリ/コンテンツのためのメモ

1. 新しいアプリは `apps/<name>/` に配置する。
2. 必要なインフラは `infra/<name>/terraform/` などに追加する。
3. デプロイ用スクリプトを `scripts/` に増やし、ルートメニュー (`site-root/`) にリンクを追加する。

この流れを踏めば、同じサーバー上に複数のサービスを安全に共存させることができます。
