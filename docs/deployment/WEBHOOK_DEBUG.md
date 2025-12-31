# Stripe Webhook デバッグ手順（テスト環境）

## 即座に確認すべきこと

### 1. Webhookが届いているか確認

```bash
# ローカル環境の場合
# ログファイルを確認
tail -f logs/django.log | grep -i webhook

# または、Djangoのログを確認
python manage.py runserver
# 別のターミナルで
tail -f logs/django.log
```

### 2. WebhookエンドポイントのURLを確認

テスト環境のURLを確認：
- ローカル: `http://localhost:8000/stripe/webhook/`
- テスト環境: `https://your-test-app.herokuapp.com/stripe/webhook/`

### 3. Stripe CLIでWebhookをテスト（推奨）

```bash
# Stripe CLIをインストール（未インストールの場合）
# https://stripe.com/docs/stripe-cli

# Webhookをローカルに転送
stripe listen --forward-to http://localhost:8000/stripe/webhook/

# 別のターミナルで、実際のサブスクリプション更新イベントをトリガー
# または、Stripe Dashboardから手動でイベントを再送信
```

---

## 問題の特定手順

### Step 1: Webhookのログを確認

Webhook処理に詳細なログを追加しました。以下を確認：

```bash
# ログファイルを確認
tail -f logs/django.log | grep -i "subscription\|webhook\|stripe"
```

### Step 2: Webhookが届いているか確認

Webhook処理の最初にログを追加：

```python
logger.info(f"Webhook received: {event_type}")
```

### Step 3: エラーがないか確認

```bash
tail -f logs/django.log | grep -i "error\|exception\|traceback"
```

### Step 4: Stripe DashboardでWebhookイベントを確認

1. [Stripe Dashboard](https://dashboard.stripe.com/test/webhooks)（テストモード）
2. エンドポイントを選択
3. 「Events」タブで`customer.subscription.updated`イベントを確認
4. イベントをクリックして詳細を確認
5. 「Response」タブでエラーレスポンスがないか確認

---

## よくある問題

### 問題1: Webhookが届いていない

**確認方法**:
- Stripe Dashboardでイベントが表示されているか
- ログにWebhookの受信記録があるか

**解決策**:
1. WebhookエンドポイントのURLを確認
2. テスト環境のURLが正しく設定されているか確認
3. Stripe CLIでローカルに転送してテスト

### 問題2: Webhookシークレットが間違っている

**確認方法**:
```bash
# 環境変数を確認
echo $STRIPE_WEBHOOK_SECRET

# または、Djangoシェルで確認
python manage.py shell
>>> from django.conf import settings
>>> print(settings.STRIPE_WEBHOOK_SECRET)
```

**解決策**:
1. Stripe Dashboardから最新のシークレットを取得
2. 環境変数に設定
3. アプリを再起動

### 問題3: サブスクリプションが見つからない

**確認方法**:
```python
# Djangoシェルで確認
from scoreai.models import FirmSubscription
subscription = FirmSubscription.objects.first()
print(f"Stripe Subscription ID: {subscription.stripe_subscription_id}")
```

**解決策**:
- `stripe_subscription_id`が正しく設定されているか確認
- Webhookの`_handle_subscription_created`が正しく動作しているか確認

---

## デバッグ用のログ追加

Webhook処理に詳細なログを追加して、問題を特定しやすくします。


