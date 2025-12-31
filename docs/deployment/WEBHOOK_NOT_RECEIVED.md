# Webhookが届いていない場合の確認手順

## 現在の状況

ログに`Webhook endpoint called`が表示されていない = Webhookが届いていない

## 確認手順

### 1. Stripe DashboardでWebhookイベントを確認

1. [Stripe Dashboard（テストモード）](https://dashboard.stripe.com/test/webhooks)
2. 「Developers」→「Webhooks」を選択
3. エンドポイントが存在するか確認
4. エンドポイントをクリック
5. 「Events」タブで`customer.subscription.updated`イベントを確認
6. イベントが存在する場合：
   - イベントをクリック
   - 「Response」タブでレスポンスコードを確認
   - エラーメッセージがないか確認

### 2. WebhookエンドポイントのURLを確認

Stripe Dashboardで設定されているURL：
- ローカル: `http://localhost:8000/stripe/webhook/`
- テスト環境: `https://your-test-app.herokuapp.com/stripe/webhook/`

**重要**: テスト環境のURLが正しく設定されているか確認してください。

### 3. Webhookエンドポイントが存在するか確認

```bash
# ローカル環境で確認
curl -X POST http://localhost:8000/stripe/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# テスト環境で確認
curl -X POST https://your-test-app.herokuapp.com/stripe/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### 4. Stripe CLIでWebhookをテスト

```bash
# Stripe CLIをインストール（未インストールの場合）
# macOS: brew install stripe/stripe-cli/stripe

# Stripe CLIにログイン
stripe login

# Webhookをローカルに転送
stripe listen --forward-to http://localhost:8000/stripe/webhook/

# 別のターミナルで、サブスクリプション更新イベントをトリガー
stripe trigger customer.subscription.updated
```

### 5. 手動でWebhookイベントを再送信

Stripe Dashboardから：

1. 「Developers」→「Webhooks」→ エンドポイントを選択
2. 「Events」タブで該当のイベントを選択
3. 「Resend」ボタンをクリック
4. ログを確認: `tail -f logs/django.log`

---

## よくある原因

### 原因1: Webhookエンドポイントが設定されていない

**確認方法**:
- Stripe Dashboardでエンドポイントが存在するか確認

**解決策**:
1. Stripe Dashboard → 「Developers」→「Webhooks」
2. 「Add endpoint」をクリック
3. URLを入力: `https://your-test-app.herokuapp.com/stripe/webhook/`
4. イベントを選択:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. 「Add endpoint」をクリック

### 原因2: テスト環境のURLが間違っている

**確認方法**:
- Stripe Dashboardで設定されているURLを確認
- テスト環境の実際のURLと一致しているか確認

**解決策**:
1. テスト環境のURLを確認: `https://your-test-app.herokuapp.com/`
2. WebhookエンドポイントのURLを更新: `https://your-test-app.herokuapp.com/stripe/webhook/`

### 原因3: ローカル環境でテストしている場合

**確認方法**:
- Stripe DashboardのWebhookエンドポイントが`localhost`を指しているか確認

**解決策**:
- Stripe CLIを使用してローカルに転送（推奨）
- または、ngrokなどのツールを使用してローカル環境を公開

---

## 手動でプランを更新する方法（緊急時）

Webhookが動作しない場合の一時的な対処：

```bash
python manage.py shell
```

シェル内で実行：
```python
from scoreai.models import FirmSubscription, FirmPlan, Firm
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

# Firmを指定（実際のFirm IDに置き換え）
firm_id = "your-firm-id"  # 実際のFirm IDに置き換え
firm = Firm.objects.get(id=firm_id)

# Stripeのサブスクリプションを取得
try:
    subscription = firm.subscription
    if subscription.stripe_subscription_id:
        print(f"Stripe Subscription ID: {subscription.stripe_subscription_id}")
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
            print(f"✅ プランを更新しました: {old_plan.name} -> {new_plan.name}")
        else:
            print(f"❌ プランが見つかりません。Price ID: {price_id}")
            print("\n利用可能なプラン:")
            for plan in FirmPlan.objects.all():
                print(f"  {plan.name}:")
                print(f"    月額Price ID: {plan.stripe_price_id_monthly}")
                print(f"    年額Price ID: {plan.stripe_price_id_yearly}")
    else:
        print("❌ Stripe Subscription IDが設定されていません。")
except FirmSubscription.DoesNotExist:
    print("❌ サブスクリプションが見つかりません。")
```

---

## 次のステップ

1. **Stripe Dashboardで確認**: Webhookイベントが記録されているか確認
2. **Webhookエンドポイントの設定**: 正しいURLが設定されているか確認
3. **Stripe CLIでテスト**: ローカル環境でWebhookをテスト
4. **ログを確認**: 修正後、再度プラン変更を試してログを確認

Stripe DashboardでWebhookイベントが記録されているか確認してください。記録されていれば、WebhookエンドポイントのURL設定に問題がある可能性が高いです。


