# Webhook 405エラーの解決方法

## 問題

ログに`GET /stripe/webhook/ HTTP/1.1" 405`が表示される

## 原因

WebhookエンドポイントはPOSTリクエストのみを受け付けるが、GETリクエストが送信されている。

## 解決策

### 1. Stripe CLIの設定を確認

Stripe CLIでWebhookを転送する際、正しいURLを指定してください：

```bash
# 正しいコマンド
stripe listen --forward-to http://localhost:8000/stripe/webhook/

# 別のターミナルで、実際のサブスクリプション更新イベントをトリガー
# 注意: stripe triggerはテスト用のフィクスチャデータを使用するため、
# 実際のサブスクリプションIDと一致しない可能性があります
```

### 2. 実際のサブスクリプション更新イベントを確認

`stripe trigger`はテスト用のフィクスチャデータを使用するため、実際のサブスクリプションIDと一致しない可能性があります。

実際のサブスクリプション更新をテストするには：

1. Stripe Dashboardで実際にプランを変更
2. または、Stripe CLIで実際のサブスクリプションIDを指定

### 3. Stripe DashboardからWebhookイベントを再送信

1. [Stripe Dashboard（テストモード）](https://dashboard.stripe.com/test/webhooks)
2. エンドポイントを選択
3. 「Events」タブで`customer.subscription.updated`イベントを選択
4. 「Resend」ボタンをクリック

### 4. 実際のサブスクリプションIDでテスト

```bash
# 実際のサブスクリプションIDを取得
python manage.py shell
```

シェル内で実行：
```python
from scoreai.models import FirmSubscription
subscription = FirmSubscription.objects.first()
print(f"Stripe Subscription ID: {subscription.stripe_subscription_id}")
```

その後、Stripe Dashboardでそのサブスクリプションのプランを変更してください。

---

## 確認事項

### 1. WebhookエンドポイントがPOSTを受け付けているか

```bash
# テスト
curl -X POST http://localhost:8000/stripe/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### 2. Stripe CLIが正しく動作しているか

```bash
# Stripe CLIでWebhookを転送
stripe listen --forward-to http://localhost:8000/stripe/webhook/

# 別のターミナルでログを確認
tail -f logs/django.log | grep -i webhook
```

### 3. 実際のプラン変更をテスト

Stripe Dashboardで実際にプランを変更して、Webhookが届くか確認してください。


