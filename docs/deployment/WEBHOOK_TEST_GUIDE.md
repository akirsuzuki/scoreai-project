# Stripe Webhook テストガイド

## テスト環境でのWebhook確認手順

### 1. Webhookが届いているか確認

#### 方法A: ログを確認

```bash
# リアルタイムでログを確認
tail -f logs/django.log | grep -i "webhook\|subscription\|stripe"

# または、すべてのログを確認
tail -f logs/django.log
```

#### 方法B: Stripe Dashboardで確認

1. [Stripe Dashboard（テストモード）](https://dashboard.stripe.com/test/webhooks)
2. 「Developers」→「Webhooks」を選択
3. エンドポイントを選択
4. 「Events」タブで最近のイベントを確認
5. `customer.subscription.updated`イベントが存在するか確認
6. イベントをクリックして詳細を確認
7. 「Response」タブでレスポンスコードを確認（200が正常）

### 2. WebhookエンドポイントのURLを確認

テスト環境のURLを確認：
- ローカル: `http://localhost:8000/stripe/webhook/`
- テスト環境: `https://your-test-app.herokuapp.com/stripe/webhook/`

Stripe Dashboardで設定されているURLと一致しているか確認してください。

### 3. Stripe CLIでWebhookをテスト（推奨）

```bash
# Stripe CLIをインストール（未インストールの場合）
# macOS: brew install stripe/stripe-cli/stripe
# または: https://stripe.com/docs/stripe-cli

# Stripe CLIにログイン
stripe login

# Webhookをローカルに転送
stripe listen --forward-to http://localhost:8000/stripe/webhook/

# 別のターミナルで、サブスクリプション更新イベントをトリガー
stripe trigger customer.subscription.updated
```

### 4. 手動でWebhookイベントを再送信

Stripe Dashboardから：

1. 「Developers」→「Webhooks」→ エンドポイントを選択
2. 「Events」タブで該当のイベントを選択
3. 「Resend」ボタンをクリック

---

## ログで確認すべきメッセージ

### 正常な場合

```
INFO ... Webhook endpoint called
INFO ... Request method: POST
INFO ... Request path: /stripe/webhook/
INFO ... Webhook secret exists: True
INFO ... Signature header exists: True
INFO ... Payload length: XXX bytes
INFO ... Webhook event constructed successfully. Event ID: evt_...
INFO ... Webhook event received: customer.subscription.updated
INFO ... Processing subscription.updated event
INFO ... Handling subscription.updated for: sub_...
INFO ... Found subscription: ... (Plan: ...)
INFO ... Subscription items: 1 items found
INFO ... New price_id: price_..., Current price_id: price_...
INFO ... Plan changed for subscription ...: ... -> ...
INFO ... Subscription updated: ... (status: active, plan: ...)
INFO ... Webhook event processed successfully: customer.subscription.updated
```

### エラーの場合

#### Webhookが届いていない
- ログに`Webhook endpoint called`が表示されない
- → Webhookエンドポイントが呼び出されていない

#### シークレットが間違っている
```
ERROR ... Invalid signature: ...
ERROR ... Expected secret: whsec_...
```
→ `STRIPE_WEBHOOK_SECRET`を確認

#### サブスクリプションが見つからない
```
WARNING ... Subscription not found: sub_...
```
→ `FirmSubscription.stripe_subscription_id`を確認

#### プランが見つからない
```
WARNING ... Plan not found for price_id: price_...
```
→ `FirmPlan.stripe_price_id_monthly`または`stripe_price_id_yearly`を確認

---

## デバッグ用の一時的な設定

### Webhookシークレットを一時的に無効化（テスト用）

**注意**: 本番環境では絶対に使用しないでください。

```python
# stripe_webhook_views.py で一時的にシークレット検証をスキップ
# （テスト環境のみ）
if settings.DEBUG:
    # シークレット検証をスキップ（テスト用）
    event = json.loads(payload)
else:
    event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
```

---

## 手動でプランを更新する方法（緊急時）

Webhookが動作しない場合の一時的な対処：

```bash
python manage.py shell
```

シェル内で実行：
```python
from scoreai.models import FirmSubscription, FirmPlan
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

# Firmを指定（実際のFirm IDに置き換え）
firm_id = "your-firm-id"
from scoreai.models import Firm
firm = Firm.objects.get(id=firm_id)

# Stripeのサブスクリプションを取得
try:
    subscription = firm.subscription
    if subscription.stripe_subscription_id:
        stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
        
        # Price IDを取得
        price_id = stripe_sub.items.data[0].price.id
        print(f"Stripe Price ID: {price_id}")
        
        # プランを特定
        new_plan = FirmPlan.objects.filter(
            stripe_price_id_monthly=price_id
        ).first() or FirmPlan.objects.filter(
            stripe_price_id_yearly=price_id
        ).first()
        
        if new_plan:
            old_plan = subscription.plan
            subscription.plan = new_plan
            subscription.stripe_price_id = price_id
            subscription.status = stripe_sub.status
            subscription.save()
            print(f"プランを更新しました: {old_plan.name} -> {new_plan.name}")
        else:
            print(f"プランが見つかりません。Price ID: {price_id}")
            print("利用可能なプラン:")
            for plan in FirmPlan.objects.all():
                print(f"  {plan.name}: 月額={plan.stripe_price_id_monthly}, 年額={plan.stripe_price_id_yearly}")
    else:
        print("Stripe Subscription IDが設定されていません。")
except FirmSubscription.DoesNotExist:
    print("サブスクリプションが見つかりません。")
```

---

## 次のステップ

1. **ログを確認**: `tail -f logs/django.log`でWebhookの受信を確認
2. **Stripe Dashboardで確認**: Webhookイベントが記録されているか確認
3. **Stripe CLIでテスト**: ローカル環境でWebhookをテスト
4. **手動で更新**: 緊急時は上記の手動更新スクリプトを使用

ログの内容を共有いただければ、具体的な問題を特定できます。


