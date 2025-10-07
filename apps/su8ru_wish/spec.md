````markdown
# Amazon ほしい物リスト変更検知 & Slack 通知ジョブ（仕様書）

## 概要
EC2 上で 1 日 1 回実行し、Amazon の特定の公開ほしい物リストの内容を取得。  
**追加・削除・価格変更** を検知して Slack Webhook に通知する。  
実装は Python を想定。複数サイト対応や拡張性は不要。

---

## 対象リスト
- URL: `https://www.amazon.co.jp/hz/wishlist/ls/20XG7YB46EBUX`
- 公開リストであるため、認証は不要。
- 通信時は User-Agent と Accept-Language を指定。

---

## 実行条件
- **頻度**: 1日1回（JST 09:00）
- **環境**: EC2（常時稼働）
- **スケジューラ**: systemd timer または cron
- **通知先**: Slack Webhook  
  `https://hooks.slack.com/services/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`

---

## データ構造
ローカルに JSON で直近状態を保存する。  
保存パス例: `/var/lib/wishlist/state_friend.json`

```json
{
  "last_checked_at": "2025-10-07T09:00:00+09:00",
  "items": [
    { "id": "ASIN-or-hash", "title": "商品名", "price": 3980.0, "url": "https://..." }
  ]
}
````

* **id**: `/dp/<ASIN>/` から取得。なければ `(title+url)` の SHA1。
* **price**: JPY 数値。価格不明なら `null`。
* **url**: 商品詳細ページ。

---

## 検知ロジック

| 種別   | 判定条件                              | 備考               |
| ---- | --------------------------------- | ---------------- |
| 追加   | `new_ids - old_ids`               | 新規商品             |
| 削除   | `old_ids - new_ids`               | 削除・在庫切れ          |
| 価格変更 | 同一 `id` で価格不一致                    | `null` 含む場合も変更扱い |
| 総額   | `sum(price)` (`price != null` のみ) | Slack 通知に表示      |

---

## Slack 通知フォーマット（例）

```text
友人WL 更新 (変化あり)
総額: ¥23,480

【追加】
- 商品A (¥3,980)
- 商品B (¥1,580)

【削除】
- 商品C

【価格変更】
- 商品D: ¥5,980 → ¥4,980 (-¥1,000)
```

* 変化がない場合：「変化なし」メッセージのみ送信
* 初回実行時は差分を送らずベースライン確立のみ可

---

## HTML 解析指針（Amazon 固定）

* 要素例：

  * タイトル: `.a-link-normal` 内テキスト
  * 価格: `.a-price-whole`（または `.a-price .a-offscreen`）
  * 商品リンク: `<a href="/dp/...">`
* `requests` + `BeautifulSoup` で解析。
* レート制限 (429) 発生時は指数バックオフ。

---

## エラー処理

* 通信失敗 or HTML構造変更 → Slack にエラーメッセージ送信。
* 例外発生時も exit code 0（cron 落ち防止）。

---

## スケジューリング案

### systemd timer

`/etc/systemd/system/wishlist.service`

```ini
[Service]
Type=oneshot
Environment=LIST_URL=https://www.amazon.co.jp/hz/wishlist/ls/20XG7YB46EBUX
Environment=WEBHOOK_URL=https://hooks.slack.com/services/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
Environment=STATE_DIR=/var/lib/wishlist
ExecStart=/usr/bin/python3 /opt/wishlist/watcher.py
```

`/etc/systemd/system/wishlist.timer`

```ini
[Timer]
OnCalendar=*-*-* 00:00:00
Persistent=true
Unit=wishlist.service
```

### cron 代替案

```
0 9 * * * LIST_URL='https://www.amazon.co.jp/hz/wishlist/ls/20XG7YB46EBUX' \
WEBHOOK_URL='https://hooks.slack.com/services/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' \
STATE_DIR='/var/lib/wishlist' \
/usr/bin/python3 /opt/wishlist/watcher.py >> /var/log/wishlist.log 2>&1
```

---

## 実装タスク一覧（Codex向け）

1. `/opt/wishlist/watcher.py` を作成

   * HTML取得 → 解析 → 差分検知 → Slack通知
2. JSON状態ファイル `/var/lib/wishlist/state_friend.json` を保存
3. 初回実行時は差分送信せずベースラインのみ作成
4. 1日1回自動実行（systemd timer または cron）
5. Slack Webhook で結果通知

---

```